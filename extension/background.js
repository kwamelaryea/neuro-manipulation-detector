// Service worker: relays ANALYZE and DEEP_ANALYZE requests to the backend.
// Opens the side panel when the extension icon is clicked.

chrome.runtime.onInstalled.addListener(async () => {
  // Migrate API key from sync → local (one-time, after H2 storage change)
  const { zdriveApiKey: localKey } = await chrome.storage.local.get("zdriveApiKey");
  if (!localKey) {
    const { zdriveApiKey: syncKey } = await chrome.storage.sync.get("zdriveApiKey");
    if (syncKey) {
      await chrome.storage.local.set({ zdriveApiKey: syncKey });
      await chrome.storage.sync.remove("zdriveApiKey");
    }
  }
});

// ── Open panel helper ─────────────────────────────────────────────────────────
// Tries Chrome's native side panel; falls back to a popup window for Arc and
// other Chromium forks that don't implement chrome.sidePanel.
async function openPanel(tabId) {
  if (chrome.sidePanel?.open) {
    try {
      await chrome.sidePanel.open({ tabId });
      return;
    } catch (_) {
      // Side panel API unavailable (Arc, other Chromium forks) — fall through
    }
  }
  chrome.windows.create({
    url: chrome.runtime.getURL("sidepanel.html"),
    type: "popup",
    width: 440,
    height: 680,
  }).catch(() => {});
}

// ── Action click ──────────────────────────────────────────────────────────────
// Top-level registration re-fires every time the SW wakes from idle, so the
// handler is never lost after Chrome kills the SW. setPanelBehavior() was
// removed: it blocked this listener on Chrome and had no effect in Arc.
chrome.action.onClicked.addListener((tab) => {
  openPanel(tab.id);
});

const DEFAULT_BACKEND = "https://zdrive-neuro-lens.kwame-laryea.workers.dev";
const LOCALHOST_BACKEND = "http://localhost:8000";

async function getSettings() {
  const { backendUrl, enabled, useLocal } = await chrome.storage.sync.get([
    "backendUrl", "enabled", "useLocal",
  ]);
  const { zdriveApiKey } = await chrome.storage.local.get("zdriveApiKey");
  return {
    backendUrl: backendUrl || DEFAULT_BACKEND,
    zdriveApiKey: zdriveApiKey || "",
    enabled: enabled !== false,
    useLocal: useLocal === true,
  };
}

async function postAnalyze(text, url, mode) {
  const { backendUrl, zdriveApiKey, useLocal } = await getSettings();
  const base = useLocal ? (backendUrl || LOCALHOST_BACKEND) : DEFAULT_BACKEND;
  const controller = new AbortController();
  const timeoutMs = mode === "deep" ? 360_000 : 30_000;
  const tid = setTimeout(() => controller.abort(), timeoutMs);
  const headers = { "Content-Type": "application/json" };
  if (zdriveApiKey && !useLocal) headers["X-ZDrive-API-Key"] = zdriveApiKey;
  try {
    const res = await fetch(`${base}/analyze`, {
      method: "POST",
      headers,
      body: JSON.stringify({ text, url: url || null, mode }),
      signal: controller.signal,
    });
    clearTimeout(tid);
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      return { ok: false, error: body.error || `HTTP ${res.status}` };
    }
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
      const { enabled } = await getSettings();
      if (!enabled) {
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
      } else {
        chrome.runtime.sendMessage({ type: "SCAN_ERROR", url: msg.url, error: result.error || "Unknown error" }).catch(() => {});
      }
    })();
    return true;
  }

  if (msg.type === "DEEP_ANALYZE") {
    // The side panel (a persistent page) owns the deep scan fetch.
    // Service workers can be killed by Chrome during a 4-min fetch, so we
    // delegate the actual HTTP call to sidepanel.js instead.
    const tabId = sender.tab?.id;
    // Open the panel so the user can watch progress (side panel or popup fallback).
    if (tabId) openPanel(tabId);
    if (tabId) chrome.tabs.sendMessage(tabId, { type: "DEEP_SCANNING" }).catch(() => {});
    // Store request so side panel can pick it up if opened after the click.
    chrome.storage.session.set({
      pendingDeepScan: { text: msg.text, url: msg.url, tabId, ts: Date.now() },
    });
    // Forward to side panel — if it's already open it handles this immediately.
    chrome.runtime.sendMessage({ type: "DO_DEEP_SCAN", text: msg.text, url: msg.url, tabId }).catch(() => {});
    return false;
  }

  return false;
});
