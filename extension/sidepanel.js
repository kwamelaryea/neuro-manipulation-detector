const DEFAULT_BACKEND = "http://localhost:8000";

// ── Plain-English label maps ───────────────────────────────────────────────

const TECHNIQUE_LABELS = {
  fear:           "Fear-based messaging",
  urgency:        "False urgency",
  tribal_identity:"Us vs. Them framing",
  reward_loop:    "Craving / reward loop",
  neutral:        "No manipulation detected",
};

const MI_LABEL = (index) => {
  if (index >= 7) return "Highly manipulative";
  if (index >= 4) return "Moderately manipulative";
  return "Not manipulative";
};

// ── State ──────────────────────────────────────────────────────────────────

let _currentUrl = "";
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
  const technique = TECHNIQUE_LABELS[data.dominant_technique] || data.dominant_technique;
  const verdict = MI_LABEL(data.manipulation_index);
  const confDesc = data.confidence === "high"
    ? "High confidence"
    : data.confidence === "medium"
    ? "Medium confidence"
    : "Low confidence";
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
          <span class="mi-verdict" style="color:${color}">${verdict}</span>
        </div>
      </div>
      <div class="mi-bar-wrap">
        <div class="mi-bar-fill" style="width:${miPct}%;background:${color}"></div>
      </div>
      <div class="bio-section-label">Brain signal breakdown</div>
      <div class="bio-bars">
        <div class="bio-bar-row" title="Predicted activity in emotional brain regions. High = content is designed to trigger feelings over rational thought.">
          <div class="bio-label-wrap">
            <span class="bio-label-main">Emotional pull</span>
            <span class="bio-label-sub">limbic system</span>
          </div>
          <div class="bio-track">
            <div class="bio-fill" style="width:${limbicPct}%;background:#8B5CF6"></div>
          </div>
          <span class="bio-val">${(data.limbic_score * 100).toFixed(0)}%</span>
        </div>
        <div class="bio-bar-row" title="Predicted activity in the rational brain. High = content engages your critical thinking rather than bypassing it.">
          <div class="bio-label-wrap">
            <span class="bio-label-main">Rational guard</span>
            <span class="bio-label-sub">prefrontal cortex</span>
          </div>
          <div class="bio-track">
            <div class="bio-fill" style="width:${pfcPct}%;background:#14B8A6"></div>
          </div>
          <span class="bio-val">${(data.pfc_score * 100).toFixed(0)}%</span>
        </div>
      </div>
      <div class="pill-row">
        <span class="pill ${confClass}">${confDesc}</span>
        <span class="pill pill-technique">${technique}</span>
      </div>
    </div>
  `;
}

function showFastResult(url, data) {
  _currentUrl = url || _currentUrl;
  document.getElementById("urlBar").textContent = _currentUrl || "—";
  document.getElementById("fastResult").innerHTML = scoreCardHTML(data, "FAST SCAN", "LLM");
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

// ── Deep scan — runs directly in the side panel page (not in the SW) ───────

async function runDeepScan(text, url, tabId) {
  if (_deepRunning) return;
  _deepRunning = true;
  showDeepScanning();

  const { backendUrl, zdriveApiKey, useLocal } = await chrome.storage.sync.get([
    "backendUrl", "zdriveApiKey", "useLocal",
  ]);
  const base = useLocal ? "http://localhost:8000" : (backendUrl || DEFAULT_BACKEND);

  try {
    const headers = { "Content-Type": "application/json" };
    if (zdriveApiKey && !useLocal) headers["X-ZDrive-API-Key"] = zdriveApiKey;
    const controller = new AbortController();
    const tid = setTimeout(() => controller.abort(), 360_000);
    const res = await fetch(`${base}/analyze`, {
      method: "POST",
      headers,
      body: JSON.stringify({ text, url: url || null, mode: "deep" }),
      signal: controller.signal,
    });
    clearTimeout(tid);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();

    showDeepResult(data);
    chrome.storage.session.set({ lastDeepResult: { data, url, ts: Date.now() } });
    chrome.storage.session.remove("pendingDeepScan");

    // Update badge on the page that triggered the scan.
    if (tabId) {
      chrome.tabs.sendMessage(tabId, { type: "DEEP_RESULT", ok: true, data }).catch(() => {});
    }
  } catch (e) {
    const errMsg = e.name === "AbortError" ? "Timed out after 6 min" : String(e);
    showDeepError(errMsg);
    chrome.storage.session.remove("pendingDeepScan");
    if (tabId) {
      chrome.tabs.sendMessage(tabId, { type: "DEEP_RESULT", ok: false, error: errMsg }).catch(() => {});
    }
  }
}

// ── Deep scan button (panel-triggered) ─────────────────────────────────────

function attachDeepBtn() {
  const btn = document.getElementById("deepBtn");
  if (!btn) return;
  btn.addEventListener("click", async () => {
    if (_deepRunning) return;
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab) return;
    chrome.tabs.sendMessage(tab.id, { type: "GET_TEXT" }, (resp) => {
      if (chrome.runtime.lastError || !resp?.text) return;
      // Tell badge to show scanning state immediately.
      chrome.tabs.sendMessage(tab.id, { type: "DEEP_SCANNING" }).catch(() => {});
      runDeepScan(resp.text, tab.url, tab.id);
    });
  });
}

// ── Incoming messages ───────────────────────────────────────────────────────

chrome.runtime.onMessage.addListener((msg) => {
  if (msg.type === "PAGE_RESULT" && msg.ok !== false) {
    showFastResult(msg.url, msg.data);
    attachDeepBtn();
  }
  if (msg.type === "DO_DEEP_SCAN") {
    // Background forwarded a badge-triggered deep scan; panel does the actual fetch.
    runDeepScan(msg.text, msg.url, msg.tabId);
  }
  if (msg.type === "DEEP_SCANNING") {
    showDeepScanning();
  }
});

// Reset panel when user switches tabs.
chrome.tabs.onActivated.addListener(() => {
  document.getElementById("fastResult").innerHTML = `
    <div class="waiting">
      <img class="waiting-icon" src="icons/icon32.png" alt="" />
      <div class="waiting-text">Scroll the page to trigger<br>a real-time scan</div>
    </div>
  `;
  document.getElementById("deepSection").style.display = "none";
  document.getElementById("deepResult").innerHTML = "";
  document.getElementById("urlBar").textContent = "Scanning new page…";
  _deepRunning = false;
});

// ── Settings ────────────────────────────────────────────────────────────────

async function loadSettings() {
  const { backendUrl, zdriveApiKey, enabled, useLocal } = await chrome.storage.sync.get([
    "backendUrl", "zdriveApiKey", "enabled", "useLocal",
  ]);
  document.getElementById("zdriveApiKey").value = zdriveApiKey || "";
  document.getElementById("backendUrl").value = backendUrl || DEFAULT_BACKEND;
  document.getElementById("enabled").checked = enabled !== false;
  document.getElementById("useLocal").checked = useLocal === true;
  toggleLocalFields(useLocal === true);
}

function toggleLocalFields(isLocal) {
  const show = isLocal;
  document.getElementById("backendUrl").style.display = show ? "block" : "none";
  document.getElementById("backendUrlLabel").style.display = show ? "block" : "none";
}

document.getElementById("useLocal").addEventListener("change", (e) => {
  toggleLocalFields(e.target.checked);
});

document.getElementById("settingsToggle").addEventListener("click", () => {
  document.getElementById("settingsSection").classList.toggle("open");
});

document.getElementById("saveBtn").addEventListener("click", async () => {
  const zdriveApiKey = document.getElementById("zdriveApiKey").value.trim();
  const backendUrl = document.getElementById("backendUrl").value.trim() || DEFAULT_BACKEND;
  const enabled = document.getElementById("enabled").checked;
  const useLocal = document.getElementById("useLocal").checked;
  await chrome.storage.sync.set({ zdriveApiKey, backendUrl, enabled, useLocal });
  const s = document.getElementById("saveStatus");
  s.textContent = "Saved.";
  setTimeout(() => (s.textContent = ""), 1500);
});

// ── Init ────────────────────────────────────────────────────────────────────

async function init() {
  await loadSettings();

  const { lastResult, lastDeepResult, pendingDeepScan } = await chrome.storage.session.get([
    "lastResult",
    "lastDeepResult",
    "pendingDeepScan",
  ]);

  if (lastResult?.data) {
    showFastResult(lastResult.url, lastResult.data);
    attachDeepBtn();
  } else {
    // Panel opened before any scroll — ask content script to scan now.
    const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
    if (tabs[0]) chrome.tabs.sendMessage(tabs[0].id, { type: "SCAN_NOW" }).catch(() => {});
  }

  if (lastDeepResult?.data) {
    showDeepResult(lastDeepResult.data);
  } else if (pendingDeepScan && !_deepRunning) {
    // Badge triggered scan before panel was open — resume it now.
    const { text, url, tabId, ts } = pendingDeepScan;
    if (Date.now() - ts < 300_000) {
      runDeepScan(text, url, tabId);
    } else {
      chrome.storage.session.remove("pendingDeepScan");
    }
  }
}

document.addEventListener("DOMContentLoaded", init);
