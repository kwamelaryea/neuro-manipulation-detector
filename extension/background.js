// Service worker: relays ANALYZE and DEEP_ANALYZE requests to the backend.
// Opens the side panel when the extension icon is clicked.

chrome.runtime.onInstalled.addListener(() => {
  chrome.sidePanel.setPanelBehavior({ openPanelOnActionClick: true });
});

const DEFAULT_BACKEND = "http://localhost:8000";

async function getBackendUrl() {
  const { backendUrl } = await chrome.storage.sync.get("backendUrl");
  return backendUrl || DEFAULT_BACKEND;
}

async function getEnabled() {
  const { enabled } = await chrome.storage.sync.get("enabled");
  return enabled !== false;
}

async function postAnalyze(text, url, mode) {
  const base = await getBackendUrl();
  const controller = new AbortController();
  // Deep scan takes ~4 min; fast scan should be <10s.
  const timeoutMs = mode === "deep" ? 360_000 : 30_000;
  const tid = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(`${base}/analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, url: url || null, mode }),
      signal: controller.signal,
    });
    clearTimeout(tid);
    if (!res.ok) return { ok: false, error: `HTTP ${res.status}` };
    const data = await res.json();
    return { ok: true, data };
  } catch (e) {
    clearTimeout(tid);
    return { ok: false, error: String(e) };
  }
}

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.type === "ANALYZE") {
    (async () => {
      if (!(await getEnabled())) {
        sendResponse({ ok: false, disabled: true });
        return;
      }
      const result = await postAnalyze(msg.text, msg.url, "fast");
      sendResponse(result);
      if (result.ok) {
        // Forward to side panel and persist for when panel opens late.
        const payload = { type: "PAGE_RESULT", url: msg.url, data: result.data };
        chrome.storage.session.set({ lastResult: { ...payload, ts: Date.now() } });
        chrome.runtime.sendMessage(payload).catch(() => {});
      }
    })();
    return true;
  }

  if (msg.type === "DEEP_ANALYZE") {
    const tabId = sender.tab?.id;
    (async () => {
      const scanningMsg = { type: "DEEP_SCANNING", url: msg.url };
      chrome.runtime.sendMessage(scanningMsg).catch(() => {});
      if (tabId) chrome.tabs.sendMessage(tabId, scanningMsg).catch(() => {});

      const result = await postAnalyze(msg.text, msg.url, "deep");
      const deepMsg = { type: "DEEP_RESULT", url: msg.url, ...result };
      if (result.ok) {
        chrome.storage.session.set({ lastDeepResult: { ...deepMsg, ts: Date.now() } });
      }
      chrome.runtime.sendMessage(deepMsg).catch(() => {});
      if (tabId) chrome.tabs.sendMessage(tabId, deepMsg).catch(() => {});
    })();
    return false;
  }

  return false;
});
