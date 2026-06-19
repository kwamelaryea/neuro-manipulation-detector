// Content script: extract visible text on scroll, dedupe, send to backend,
// render an overlay badge.

const SEEN = new Set();        // SHA-like dedupe by normalized text
const MIN_CHARS = 40;          // skip trivially short snippets
const MAX_CHARS = 4000;        // cap payload size
const DEBOUNCE_MS = 600;

let debounceTimer = null;
let _lastText = "";            // stored for Deep Scan button

// --- visibility helpers ---------------------------------------------------

function isVisible(el) {
  const rect = el.getBoundingClientRect();
  if (rect.width === 0 || rect.height === 0) return false;
  // Must intersect the viewport.
  if (rect.bottom < 0 || rect.top > window.innerHeight) return false;
  const style = window.getComputedStyle(el);
  if (style.display === "none" || style.visibility === "hidden" || style.opacity === "0") {
    return false;
  }
  return true;
}

function extractVisibleText() {
  // Prefer semantic content blocks; fall back to paragraphs.
  const candidates = document.querySelectorAll(
    "p, article, h1, h2, h3, li, blockquote, [role='article']"
  );
  const parts = [];
  for (const el of candidates) {
    if (!isVisible(el)) continue;
    const t = (el.innerText || "").trim();
    if (t.length >= 20) parts.push(t);
  }
  let text = parts.join(" ").replace(/\s+/g, " ").trim();
  if (text.length > MAX_CHARS) text = text.slice(0, MAX_CHARS);
  return text;
}

function normalize(text) {
  return text.trim().toLowerCase();
}

// --- analysis flow --------------------------------------------------------

function analyzeNow() {
  const text = extractVisibleText();
  if (text.length < MIN_CHARS) return;
  _lastText = text;

  const key = normalize(text);
  if (SEEN.has(key)) return;
  SEEN.add(key);

  chrome.runtime.sendMessage(
    { type: "ANALYZE", text, url: location.href },
    (resp) => {
      if (chrome.runtime.lastError) return; // worker asleep / no listener
      if (!resp || !resp.ok) return;
      renderBadge(resp.data, null);
    }
  );
}

function scheduleAnalyze() {
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(analyzeNow, DEBOUNCE_MS);
}

window.addEventListener("scroll", scheduleAnalyze, { passive: true });
window.addEventListener("load", scheduleAnalyze);

// --- overlay --------------------------------------------------------------

function badgeColor(index) {
  if (index >= 7) return "#DC2626";
  if (index >= 4) return "#D97706";
  return "#16A34A";
}

function renderBadge(data, scorerLabel) {
  let badge = document.getElementById("nmd-badge");
  if (!badge) {
    badge = document.createElement("div");
    badge.id = "nmd-badge";
    document.body.appendChild(badge);
    badge.addEventListener("click", (e) => {
      // Don't toggle when clicking the deep scan button.
      if (e.target.classList.contains("nmd-deep-btn")) return;
      badge.classList.toggle("nmd-expanded");
    });
  }
  badge.classList.remove("nmd-scanning");
  const color = badgeColor(data.manipulation_index);
  badge.style.setProperty("--nmd-accent", color);

  const sourceRow = scorerLabel
    ? `<div class="nmd-row nmd-source-row"><span>Source</span><span class="nmd-tribe-tag">${scorerLabel}</span></div>`
    : "";
  const deepBtn = scorerLabel === "TRIBE v2"
    ? "" // already ran deep scan
    : `<button class="nmd-deep-btn" title="Run TRIBE v2 neural inference (~4 min)">🔬 Deep Scan</button>`;

  badge.innerHTML = `
    <div class="nmd-row nmd-headline">
      <span class="nmd-dot"></span>
      <span class="nmd-mi">${data.manipulation_index.toFixed(1)}</span>
      <span class="nmd-label">manipulation</span>
    </div>
    <div class="nmd-detail">
      <div class="nmd-row"><span>Limbic</span><span>${(data.limbic_score * 100).toFixed(0)}%</span></div>
      <div class="nmd-row"><span>PFC</span><span>${(data.pfc_score * 100).toFixed(0)}%</span></div>
      <div class="nmd-row"><span>Technique</span><span>${data.dominant_technique}</span></div>
      <div class="nmd-row"><span>Confidence</span><span>${data.confidence}</span></div>
      ${sourceRow}
      ${deepBtn}
    </div>
  `;

  const btn = badge.querySelector(".nmd-deep-btn");
  if (btn) {
    btn.addEventListener("click", () => {
      if (!_lastText) return;
      badge.classList.add("nmd-scanning");
      badge.innerHTML = `
        <div class="nmd-row nmd-headline">
          <span class="nmd-dot"></span>
          <span class="nmd-mi">…</span>
          <span class="nmd-label">TRIBE v2 scanning</span>
        </div>
      `;
      // Guard against "Extension context invalidated" if the extension was
      // reloaded while this content script was still alive.
      try {
        if (chrome.runtime?.id) {
          chrome.runtime.sendMessage({ type: "DEEP_ANALYZE", text: _lastText, url: location.href });
        } else {
          throw new Error("context invalidated");
        }
      } catch (_) {
        badge.classList.remove("nmd-scanning");
        badge.innerHTML += `
          <div style="color:#D97706;font-size:10px;margin-top:4px">
            Reload the page to re-enable NMD
          </div>
        `;
      }
    });
  }
}

// --- messages from background / side panel --------------------------------

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg.type === "GET_TEXT") {
    sendResponse({ text: _lastText || extractVisibleText() });
    return true;
  }
  if (msg.type === "SCAN_NOW") {
    // Side panel requested an immediate scan (e.g. opened before any scroll).
    const text = extractVisibleText();
    if (text.length >= MIN_CHARS) {
      _lastText = text;
      chrome.runtime.sendMessage({ type: "ANALYZE", text, url: location.href }, (resp) => {
        if (chrome.runtime.lastError) return;
        if (!resp || !resp.ok) return;
        renderBadge(resp.data, null);
      });
    }
    return true;
  }
  if (msg.type === "DEEP_SCANNING") {
    const badge = document.getElementById("nmd-badge");
    if (badge) badge.classList.add("nmd-scanning");
  }
  if (msg.type === "DEEP_RESULT") {
    if (msg.ok && msg.data) {
      renderBadge(msg.data, "TRIBE v2");
      const badge = document.getElementById("nmd-badge");
      if (badge) badge.classList.add("nmd-expanded");
    } else {
      const badge = document.getElementById("nmd-badge");
      if (badge) {
        badge.classList.remove("nmd-scanning");
        badge.innerHTML += `<div style="color:#DC2626;font-size:11px;margin-top:6px">Deep scan failed: ${msg.error || "unknown"}</div>`;
      }
    }
  }
});
