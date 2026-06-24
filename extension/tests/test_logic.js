/**
 * Extension logic unit tests — runs with Node.js, no browser needed.
 * Tests pure functions extracted from extension code.
 * Run: node extension/tests/test_logic.js
 */

let passed = 0;
let failed = 0;

function assert(condition, msg) {
  if (condition) { passed++; console.log(`  ✓ ${msg}`); }
  else { failed++; console.error(`  ✗ ${msg}`); }
}

// ── esc() — HTML escaper (security-critical) ────────────────────────────────

function esc(s) {
  return String(s).replace(/[<>&"']/g, c => ({ '<': '&lt;', '>': '&gt;', '&': '&amp;', '"': '&quot;', "'": '&#39;' })[c]);
}

console.log('\n== esc() ==');
assert(esc('<script>') === '&lt;script&gt;', 'escapes angle brackets');
assert(esc('a&b') === 'a&amp;b', 'escapes ampersand');
assert(esc('"hello"') === '&quot;hello&quot;', 'escapes double quotes');
assert(esc("it's") === "it&#39;s", 'escapes single quotes');
assert(esc('<img onerror="alert(1)">') === '&lt;img onerror=&quot;alert(1)&quot;&gt;', 'escapes XSS payload');
assert(esc('normal text') === 'normal text', 'passes through safe text');
assert(esc('') === '', 'handles empty string');
assert(esc(123) === '123', 'coerces number to string');
assert(esc(null) === 'null', 'coerces null to string');
assert(esc(undefined) === 'undefined', 'coerces undefined to string');
assert(esc(0) === '0', 'coerces zero to string');
assert(esc('<think>{"fake":true}</think>') === '&lt;think&gt;{&quot;fake&quot;:true}&lt;/think&gt;', 'escapes Qwen3 thinking tags');

// ── URL routing logic (mirrors background.js postAnalyze) ────────────────────

const DEFAULT_BACKEND = "https://zdrive-neuro-lens.kwame-laryea.workers.dev";
const LOCALHOST_BACKEND = "http://localhost:8000";

function resolveBase(useLocal, backendUrl) {
  return useLocal ? (backendUrl || LOCALHOST_BACKEND) : DEFAULT_BACKEND;
}

console.log('\n== URL routing ==');
assert(resolveBase(false, '') === DEFAULT_BACKEND, 'production mode → CF Worker');
assert(resolveBase(false, 'http://localhost:8000') === DEFAULT_BACKEND, 'production mode ignores stored localhost');
assert(resolveBase(false, 'http://custom.example.com') === DEFAULT_BACKEND, 'production mode ignores custom URL');
assert(resolveBase(true, '') === LOCALHOST_BACKEND, 'local mode → localhost fallback');
assert(resolveBase(true, 'http://custom:9000') === 'http://custom:9000', 'local mode uses custom URL');
assert(resolveBase(true, null) === LOCALHOST_BACKEND, 'local mode with null → localhost');
assert(resolveBase(true, undefined) === LOCALHOST_BACKEND, 'local mode with undefined → localhost');

// ── Settings save logic (mirrors sidepanel.js save handler) ────────────────

function resolveBackendUrlForSave(useLocal, fieldValue) {
  return useLocal ? (fieldValue || LOCALHOST_BACKEND) : "";
}

console.log('\n== Settings save ==');
assert(resolveBackendUrlForSave(false, 'http://localhost:8000') === '', 'production mode saves empty backendUrl');
assert(resolveBackendUrlForSave(false, '') === '', 'production mode with empty field saves empty');
assert(resolveBackendUrlForSave(true, 'http://localhost:8000') === 'http://localhost:8000', 'local mode saves the URL');
assert(resolveBackendUrlForSave(true, '') === LOCALHOST_BACKEND, 'local mode with empty saves fallback');

// ── getSettings defaults (mirrors background.js) ─────────────────────────────

function getSettingsDefaults(stored) {
  return {
    backendUrl: stored.backendUrl || DEFAULT_BACKEND,
    zdriveApiKey: stored.zdriveApiKey || "",
    enabled: stored.enabled !== false,
    useLocal: stored.useLocal === true,
  };
}

console.log('\n== getSettings defaults ==');

const s1 = getSettingsDefaults({});
assert(s1.backendUrl === DEFAULT_BACKEND, 'empty storage → default backend');
assert(s1.zdriveApiKey === '', 'empty storage → empty key');
assert(s1.enabled === true, 'empty storage → enabled by default');
assert(s1.useLocal === false, 'empty storage → not local');

const s2 = getSettingsDefaults({ enabled: false });
assert(s2.enabled === false, 'explicitly disabled');

const s3 = getSettingsDefaults({ useLocal: true });
assert(s3.useLocal === true, 'explicitly local');

const s4 = getSettingsDefaults({ useLocal: "yes" });
assert(s4.useLocal === false, 'truthy non-boolean useLocal → false');

const s5 = getSettingsDefaults({ enabled: undefined });
assert(s5.enabled === true, 'undefined enabled → true (not false)');

// ── API key header logic (mirrors background.js postAnalyze) ─────────────────

function shouldSendApiKey(zdriveApiKey, useLocal) {
  return !!(zdriveApiKey && !useLocal);
}

console.log('\n== API key header logic ==');
assert(shouldSendApiKey('znl_abc123', false) === true, 'has key + production → send');
assert(shouldSendApiKey('znl_abc123', true) === false, 'has key + local → skip');
assert(shouldSendApiKey('', false) === false, 'empty key + production → skip');
assert(shouldSendApiKey(undefined, false) === false, 'undefined key → skip');
assert(shouldSendApiKey(null, false) === false, 'null key → skip');

// ── MI color/verdict logic ──────────────────────────────────────────────────

function badgeColor(index) {
  if (index >= 7) return "#DC2626";
  if (index >= 4) return "#D97706";
  return "#16A34A";
}

function badgeVerdict(index) {
  if (index >= 7) return "High manipulation";
  if (index >= 4) return "Some manipulation";
  return "Not manipulative";
}

console.log('\n== MI scoring display ==');
assert(badgeColor(0) === '#16A34A', 'MI 0 → green');
assert(badgeColor(3.9) === '#16A34A', 'MI 3.9 → green');
assert(badgeColor(4) === '#D97706', 'MI 4 → amber');
assert(badgeColor(6.9) === '#D97706', 'MI 6.9 → amber');
assert(badgeColor(7) === '#DC2626', 'MI 7 → red');
assert(badgeColor(10) === '#DC2626', 'MI 10 → red');
assert(badgeVerdict(2) === 'Not manipulative', 'low MI verdict');
assert(badgeVerdict(5) === 'Some manipulation', 'mid MI verdict');
assert(badgeVerdict(8) === 'High manipulation', 'high MI verdict');

// ── Boundary: MI = 7 triggers CTA ──────────────────────────────────────────

console.log('\n== CTA threshold ==');
assert(6.99 < 7, 'MI 6.99 → no CTA');
assert(7.0 >= 7, 'MI 7.0 → CTA shown');
assert(10 >= 7, 'MI 10 → CTA shown');

// ── Text extraction bounds ──────────────────────────────────────────────────

const MIN_CHARS = 40;
const MAX_CHARS = 4000;

console.log('\n== Text bounds ==');
assert('x'.repeat(39).length < MIN_CHARS, '39 chars → too short, skip');
assert('x'.repeat(40).length >= MIN_CHARS, '40 chars → minimum threshold');
assert('x'.repeat(5000).slice(0, MAX_CHARS).length === MAX_CHARS, 'text capped at 4000');

// ── Report ──────────────────────────────────────────────────────────────────

console.log(`\n${'='.repeat(40)}`);
console.log(`Results: ${passed} passed, ${failed} failed`);
process.exit(failed > 0 ? 1 : 0);
