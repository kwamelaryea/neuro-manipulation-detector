// Content script: extract visible text on scroll, dedupe, send to backend,
// render an overlay badge.

const SEEN = new Set();        // SHA-like dedupe by normalized text
const MIN_CHARS = 40;          // skip trivially short snippets
const MAX_CHARS = 4000;        // cap payload size
const DEBOUNCE_MS = 600;

let debounceTimer = null;

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

  const key = normalize(text);
  if (SEEN.has(key)) return;
  SEEN.add(key);

  chrome.runtime.sendMessage(
    { type: "ANALYZE", text, url: location.href },
    (resp) => {
      if (chrome.runtime.lastError) return; // worker asleep / no listener
      if (!resp || !resp.ok) return;
      renderBadge(resp.data);
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
  if (index >= 7) return "#DC2626"; // red — high manipulation
  if (index >= 4) return "#D97706"; // amber — moderate
  return "#16A34A";                 // green — low
}

function renderBadge(data) {
  let badge = document.getElementById("nmd-badge");
  if (!badge) {
    badge = document.createElement("div");
    badge.id = "nmd-badge";
    document.body.appendChild(badge);
    badge.addEventListener("click", () => {
      badge.classList.toggle("nmd-expanded");
    });
  }
  const color = badgeColor(data.manipulation_index);
  badge.style.setProperty("--nmd-accent", color);
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
    </div>
  `;
}
