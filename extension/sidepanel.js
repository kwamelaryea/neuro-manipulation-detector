const DEFAULT_BACKEND = "http://localhost:8000";

// ── State ──────────────────────────────────────────────────────────────────

let _currentUrl = "";
let _lastText = "";    // stored by content.js message → background forwards it here
let _deepRunning = false;

// ── Score rendering ────────────────────────────────────────────────────────

function miColor(index) {
  if (index >= 7) return "#DC2626";
  if (index >= 4) return "#D97706";
  return "#16A34A";
}

function scoreCardHTML(data, label, scorerTag) {
  const color = miColor(data.manipulation_index);
  const miPct = Math.max(2, (data.manipulation_index / 10) * 100).toFixed(1);
  const limbicPct = Math.max(2, data.limbic_score * 100).toFixed(0);
  const pfcPct = Math.max(2, data.pfc_score * 100).toFixed(0);
  const tagClass = scorerTag === "TRIBE v2" ? "tribe" : "llm";
  const tag = scorerTag
    ? `<span class="scorer-tag ${tagClass}">${scorerTag}</span>`
    : "";
  const confClass = `pill-conf-${data.confidence}`;
  return `
    <div class="score-card">
      <div class="card-header">
        <span class="card-label">${label}</span>
        ${tag}
      </div>
      <div class="mi-display">
        <span class="mi-val" style="color:${color}">${data.manipulation_index.toFixed(1)}</span>
        <div class="mi-meta">
          <span class="mi-denom">/ 10</span>
          <span class="mi-tech">${data.dominant_technique}</span>
        </div>
      </div>
      <div class="mi-bar-wrap">
        <div class="mi-bar-fill" style="width:${miPct}%;background:${color}"></div>
      </div>
      <div class="bio-bars">
        <div class="bio-bar-row">
          <span class="bio-label" style="color:#6D28D9">Limbic</span>
          <div class="bio-track">
            <div class="bio-fill" style="width:${limbicPct}%;background:#6D28D9"></div>
          </div>
          <span class="bio-val">${(data.limbic_score * 100).toFixed(0)}%</span>
        </div>
        <div class="bio-bar-row">
          <span class="bio-label" style="color:#14B8A6">PFC</span>
          <div class="bio-track">
            <div class="bio-fill" style="width:${pfcPct}%;background:#14B8A6"></div>
          </div>
          <span class="bio-val">${(data.pfc_score * 100).toFixed(0)}%</span>
        </div>
      </div>
      <div class="pill-row">
        <span class="pill ${confClass}">${data.confidence} confidence</span>
        <span class="pill">${data.dominant_technique}</span>
      </div>
    </div>
  `;
}

function showFastResult(url, data) {
  _currentUrl = url || _currentUrl;
  document.getElementById("urlBar").textContent = _currentUrl || "—";

  document.getElementById("fastResult").innerHTML = scoreCardHTML(
    data, "FAST SCAN", "LLM"
  );

  // Show deep scan section only once we have a fast result.
  document.getElementById("deepSection").style.display = "block";
}

function showDeepScanning() {
  document.getElementById("deepTrigger").innerHTML = `
    <div class="deep-scanning">
      <div class="pulse"></div>
      TRIBE v2 neural inference running…
    </div>
  `;
}

function showDeepResult(data) {
  _deepRunning = false;
  const now = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  document.getElementById("deepTrigger").innerHTML = "";
  document.getElementById("deepResult").innerHTML = scoreCardHTML(
    data, `TRIBE v2 · ${now}`, "TRIBE v2"
  );
}

function showDeepError(msg) {
  _deepRunning = false;
  document.getElementById("deepTrigger").innerHTML = `
    <button class="deep-btn" id="deepBtn">
      🔬 Retry Deep Scan
    </button>
  `;
  document.getElementById("deepResult").innerHTML = `
    <div style="color:#DC2626;font-size:11px;padding:6px 0">
      Deep scan failed: ${msg || "unknown error"}
    </div>
  `;
  attachDeepBtn();
}

// ── Deep scan trigger ───────────────────────────────────────────────────────

function attachDeepBtn() {
  const btn = document.getElementById("deepBtn");
  if (!btn) return;
  btn.addEventListener("click", async () => {
    if (_deepRunning) return;

    // Get text from the active tab's content script.
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab) return;

    chrome.tabs.sendMessage(tab.id, { type: "GET_TEXT" }, (resp) => {
      if (chrome.runtime.lastError || !resp?.text) return;
      _deepRunning = true;
      showDeepScanning();
      chrome.runtime.sendMessage({
        type: "DEEP_ANALYZE",
        text: resp.text,
        url: tab.url,
      });
    });
  });
}

// ── Incoming messages ───────────────────────────────────────────────────────

chrome.runtime.onMessage.addListener((msg) => {
  if (msg.type === "PAGE_RESULT" && msg.ok !== false) {
    showFastResult(msg.url, msg.data);
    attachDeepBtn();
  }
  if (msg.type === "DEEP_SCANNING") {
    showDeepScanning();
  }
  if (msg.type === "DEEP_RESULT") {
    if (msg.ok && msg.data) {
      showDeepResult(msg.data);
    } else {
      showDeepError(msg.error);
    }
  }
});

// Reset panel when user navigates to a new page.
chrome.tabs.onActivated.addListener(() => {
  document.getElementById("fastResult").innerHTML = `
    <div class="waiting">
      <div class="waiting-icon">🧠</div>
      Scroll the page to trigger a scan
    </div>
  `;
  document.getElementById("deepSection").style.display = "none";
  document.getElementById("deepResult").innerHTML = "";
  document.getElementById("urlBar").textContent = "Scanning new page…";
  _deepRunning = false;
});

// ── Settings ────────────────────────────────────────────────────────────────

async function loadSettings() {
  const { backendUrl, enabled } = await chrome.storage.sync.get(["backendUrl", "enabled"]);
  document.getElementById("backendUrl").value = backendUrl || DEFAULT_BACKEND;
  document.getElementById("enabled").checked = enabled !== false;
}

document.getElementById("settingsToggle").addEventListener("click", () => {
  document.getElementById("settingsSection").classList.toggle("open");
});

document.getElementById("saveBtn").addEventListener("click", async () => {
  const backendUrl = document.getElementById("backendUrl").value.trim() || DEFAULT_BACKEND;
  const enabled = document.getElementById("enabled").checked;
  await chrome.storage.sync.set({ backendUrl, enabled });
  const s = document.getElementById("saveStatus");
  s.textContent = "Saved.";
  setTimeout(() => (s.textContent = ""), 1500);
});

// ── Init ────────────────────────────────────────────────────────────────────

async function init() {
  await loadSettings();

  // If background already has a result (e.g. panel opened after scroll), show it.
  const { lastResult, lastDeepResult } = await chrome.storage.session.get([
    "lastResult",
    "lastDeepResult",
  ]);
  if (lastResult?.data) {
    showFastResult(lastResult.url, lastResult.data);
    attachDeepBtn();
  }
  if (lastDeepResult?.data) {
    showDeepResult(lastDeepResult.data);
  }
}

document.addEventListener("DOMContentLoaded", init);
