const DEFAULT_BACKEND = "https://zdrive-neuro-lens.kwame-laryea.workers.dev";
const DEEP_BACKEND   = "https://zdrive-neuro-lens.fly.dev";
const LOCAL_BACKEND   = "http://localhost:8000";

// ── Plain-English label maps ───────────────────────────────────────────────

const TECHNIQUE_LABELS = {
  fear:           "Fear-based messaging",
  urgency:        "False urgency",
  tribal_identity:"Us vs. Them framing",
  reward_loop:    "Craving / reward loop",
  neutral:        "No manipulation detected",
};

const ROI_META = {
  insula:           { label: "Visceral urgency",   sub: "insula",              color: "#A78BFA" },
  tpj:              { label: "Emotional context",  sub: "temporo-parietal",    color: "#C084FC" },
  mtg:              { label: "Semantic affect",    sub: "middle temporal",     color: "#E879F9" },
  parahippocampal:  { label: "Emotional memory",   sub: "parahippocampal",     color: "#D946EF" },
  broca45:          { label: "Language control",   sub: "Broca's area",        color: "#2DD4BF" },
  sts:              { label: "Speech processing",  sub: "superior temporal",   color: "#5EEAD4" },
  dlpfc:            { label: "Reasoning",          sub: "dorsolateral PFC",    color: "#99F6E4" },
  acc:              { label: "Conflict monitor",   sub: "anterior cingulate",  color: "#6EE7B7" },
};

const LIMBIC_ROIS = ["insula", "tpj", "mtg", "parahippocampal"];
const PFC_ROIS = ["broca45", "sts", "dlpfc", "acc"];

const MI_LABEL = (index) => {
  if (index >= 7) return "Highly manipulative";
  if (index >= 4) return "Moderately manipulative";
  return "Not manipulative";
};

// ── State ──────────────────────────────────────────────────────────────────

let _currentUrl = "";
let _deepRunning = false;
let _lastFastData = null;

// ── Score rendering ────────────────────────────────────────────────────────

function miColor(index) {
  if (index >= 7) return "#DC2626";
  if (index >= 4) return "#D97706";
  return "#16A34A";
}

function roiSubBarsHTML(keys, roi) {
  const rows = keys.map((k) => {
    const meta = ROI_META[k];
    if (!meta || roi[k] == null) return "";
    const pct = Math.max(2, roi[k] * 100).toFixed(0);
    return `
      <div class="bio-bar-row roi-sub-row">
        <div class="bio-label-wrap">
          <span class="bio-label-main roi-sub-label">${meta.label}</span>
          <span class="bio-label-sub">${meta.sub}</span>
        </div>
        <div class="bio-track">
          <div class="bio-fill" style="width:${pct}%;background:${meta.color}"></div>
        </div>
        <span class="bio-val">${pct}%</span>
      </div>`;
  }).join("");
  return `<div class="roi-sub-bars">${rows}</div>`;
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
        ${data.roi_detail ? roiSubBarsHTML(LIMBIC_ROIS, data.roi_detail) : ""}
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
        ${data.roi_detail ? roiSubBarsHTML(PFC_ROIS, data.roi_detail) : ""}
      </div>
      <div class="pill-row">
        <span class="pill ${confClass}">${confDesc}</span>
        <span class="pill pill-technique">${technique}</span>
      </div>
      ${data.manipulation_index >= 7 ? `
      <a class="mi-cta" href="https://zdrive.io?utm_source=neuro-lens&utm_medium=extension&utm_content=high-mi-cta&utm_campaign=research-privately" target="_blank">
        <span class="mi-cta-text">Research this privately</span>
        <span class="mi-cta-sub">Ask questions where no one can see your queries</span>
      </a>` : ""}
    </div>
  `;
}

function showFastResult(url, data) {
  _currentUrl = url || _currentUrl;
  _lastFastData = data;
  document.getElementById("urlBar").textContent = _currentUrl || "—";
  document.getElementById("fastResult").innerHTML = scoreCardHTML(data, "FAST SCAN", "LLM");
  document.getElementById("deepSection").style.display = "block";
}

function collapseFastScan() {
  if (!_lastFastData) return;
  const d = _lastFastData;
  const color = miColor(d.manipulation_index);
  const technique = TECHNIQUE_LABELS[d.dominant_technique] || d.dominant_technique;
  document.getElementById("fastResult").innerHTML = `
    <div class="fast-collapsed">
      <span class="fast-collapsed-label">FAST SCAN</span>
      <span class="fast-collapsed-score" style="color:${color}">${d.manipulation_index.toFixed(1)}</span>
      <span class="fast-collapsed-sep">&middot;</span>
      <span class="fast-collapsed-technique">${technique}</span>
      <span class="scorer-tag llm">LLM</span>
    </div>
  `;
}

function showDeepScanning() {
  document.getElementById("deepTrigger").innerHTML = `
    <div class="deep-scanning">
      <div class="pulse"></div>
      Deep scan running…
    </div>
  `;
}

function showDeepResult(data) {
  _deepRunning = false;
  const now = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  document.getElementById("deepTrigger").innerHTML = "";
  const isLlmFallback = data.scorer === "llm";
  const label   = isLlmFallback ? `LLM fallback · ${now}` : `TRIBE v2 · ${now}`;
  const scorerTag = isLlmFallback ? "LLM" : "TRIBE v2";
  if (!isLlmFallback) collapseFastScan();
  document.getElementById("deepResult").innerHTML = scoreCardHTML(data, label, scorerTag)
    + (isLlmFallback
      ? `<div style="padding:6px 16px 10px;font-size:10px;color:#6B7280">
           ⚠ TRIBE v2 unavailable — LLM used instead. Scores match Fast Scan.
         </div>`
      : "");
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

  const base = useLocal ? (backendUrl || LOCAL_BACKEND) : DEEP_BACKEND;
  const trimmed = text.slice(0, 3000);
  console.log(`[NMD] Deep scan → ${base}/analyze (${trimmed.length} chars)`);

  try {
    const headers = { "Content-Type": "application/json" };
    if (zdriveApiKey && !useLocal) headers["X-ZDrive-API-Key"] = zdriveApiKey;
    const controller = new AbortController();
    const tid = setTimeout(() => controller.abort(), 360_000);
    const res = await fetch(`${base}/analyze`, {
      method: "POST",
      headers,
      body: JSON.stringify({ text: trimmed, url: url || null, mode: "deep" }),
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
    const errMsg = e.name === "AbortError" ? `Timed out (${base})` : `${e} (${base})`;
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
      <img class="waiting-icon" src="icons/glass-brain.png" alt="" />
      <div class="waiting-text">Scroll the page to trigger<br>a real-time scan</div>
    </div>
  `;
  document.getElementById("deepSection").style.display = "none";
  document.getElementById("deepResult").innerHTML = "";
  document.getElementById("urlBar").textContent = "Scanning new page…";
  _deepRunning = false;
  _lastFastData = null;
});

// ── View navigation ─────────────────────────────────────────────────────────

function showView(id) {
  document.querySelectorAll(".view").forEach((v) => v.classList.remove("active"));
  document.getElementById(id).classList.add("active");
}

document.getElementById("settingsToggle").addEventListener("click", () => {
  loadSettings().then(() => showView("settingsView"));
});

document.getElementById("backBtn").addEventListener("click", () => {
  showView("mainView");
});

// ── Settings ────────────────────────────────────────────────────────────────

function updateKeyDisplay(key) {
  const display = document.getElementById("keyDisplay");
  const text = document.getElementById("keyDisplayText");
  if (key) {
    display.classList.add("has-key");
    // Show first 8 chars + masked remainder
    const visible = key.slice(0, 8);
    text.textContent = visible + "••••••••••••";
  } else {
    display.classList.remove("has-key");
    text.textContent = "No key configured";
  }
}

async function loadSettings() {
  const { backendUrl, zdriveApiKey, enabled, useLocal } = await chrome.storage.sync.get([
    "backendUrl", "zdriveApiKey", "enabled", "useLocal",
  ]);
  document.getElementById("zdriveApiKey").value = "";  // never pre-fill password fields
  document.getElementById("backendUrl").value = backendUrl || LOCAL_BACKEND;
  document.getElementById("enabled").checked = enabled !== false;
  document.getElementById("useLocal").checked = useLocal === true;
  updateKeyDisplay(zdriveApiKey || "");
  toggleLocalFields(useLocal === true);
  // Hide save status on open
  document.getElementById("saveStatus").classList.remove("visible");
}

function toggleLocalFields(isLocal) {
  document.getElementById("customUrlGroup").style.display = isLocal ? "block" : "none";
}

document.getElementById("useLocal").addEventListener("change", (e) => {
  toggleLocalFields(e.target.checked);
});

document.getElementById("saveBtn").addEventListener("click", async () => {
  const newKey = document.getElementById("zdriveApiKey").value.trim();
  const backendUrl = document.getElementById("backendUrl").value.trim() || DEFAULT_BACKEND;
  const enabled = document.getElementById("enabled").checked;
  const useLocal = document.getElementById("useLocal").checked;

  // Only update the key if a new one was typed; otherwise keep existing
  const { zdriveApiKey: existingKey } = await chrome.storage.sync.get("zdriveApiKey");
  const zdriveApiKey = newKey || existingKey || "";

  await chrome.storage.sync.set({ zdriveApiKey, backendUrl, enabled, useLocal });
  updateKeyDisplay(zdriveApiKey);
  document.getElementById("zdriveApiKey").value = "";

  // Contextual post-save message
  let msg = "";
  if (!enabled) {
    msg = "Extension is disabled. Toggle Enabled to start scanning.";
  } else if (useLocal) {
    msg = `Scanning via local backend at ${backendUrl}. Make sure the server is running.`;
  } else if (zdriveApiKey) {
    msg = `Scanning via ZDrive Neuro Lens cloud. 1 credit per page scan. <a id="goBack">← Return to results</a>`;
  } else {
    msg = `No API key set — scans will fail. <a id="goBack">Add a key above</a> or get one at zdrive.io.`;
  }

  const statusEl = document.getElementById("saveStatus");
  document.getElementById("saveStatusBody").innerHTML = msg;
  statusEl.classList.add("visible");

  // Wire the go-back link if present
  const goBack = document.getElementById("goBack");
  if (goBack) goBack.addEventListener("click", () => showView("mainView"));
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
