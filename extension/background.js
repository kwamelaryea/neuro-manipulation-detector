// Service worker: relays ANALYZE requests from content scripts to the backend.

const DEFAULT_BACKEND = "http://localhost:8000";

async function getBackendUrl() {
  const { backendUrl } = await chrome.storage.sync.get("backendUrl");
  return backendUrl || DEFAULT_BACKEND;
}

async function getEnabled() {
  const { enabled } = await chrome.storage.sync.get("enabled");
  return enabled !== false; // default ON
}

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg.type !== "ANALYZE") return false;

  (async () => {
    if (!(await getEnabled())) {
      sendResponse({ ok: false, disabled: true });
      return;
    }
    try {
      const base = await getBackendUrl();
      const res = await fetch(`${base}/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: msg.text, url: msg.url || null }),
      });
      if (!res.ok) {
        sendResponse({ ok: false, error: `HTTP ${res.status}` });
        return;
      }
      const data = await res.json();
      sendResponse({ ok: true, data });
    } catch (e) {
      sendResponse({ ok: false, error: String(e) });
    }
  })();

  return true; // keep the message channel open for async sendResponse
});
