# Neuro Manipulation Detector — Handoff

## Status: Phase 2 DEPLOYED ✅ — Hybrid (LLM fast + TRIBE v2 deep scan)

**Last action:** Task 15 E2E browser test passed (2026-06-19).
- Daily Mail homepage → 8.0 manipulation, 82% limbic, fear, medium confidence ✅
- Daily Mail article (Vanessa Feltz) → 8.0 manipulation, 82% limbic, fear, medium confidence ✅
- Wikipedia (World Cup) → 0.6 manipulation, 5% limbic, 75% PFC, neutral, high confidence ✅
Badge renders, click-to-expand works, cache prevents duplicate calls on re-scroll.

GitHub repo: https://github.com/kwamelaryea/neuro-manipulation-detector
Branch history: all Phase 1 work on `feat/neuro-manipulation-detector`, merged to `main`.

---

## Where we are

### Phase 1 — DONE ✅ (tagged `phase-1-mvp`)
All 16 tasks complete. 28 tests passing. E2E verified.

| Component | File | Status |
|---|---|---|
| API contract | `backend/models.py` | ✅ |
| Cache (SHA256 + disk) | `backend/cache.py` | ✅ |
| TRIBE v2 rubric prompt | `backend/scorer_llm.py` | ✅ |
| LLM scorer (claude-sonnet-4-6) | `backend/scorer_llm.py` | ✅ |
| Scorer shim | `backend/scorer.py` | ✅ |
| FastAPI /analyze + CORS | `backend/main.py` | ✅ |
| MV3 manifest | `extension/manifest.json` | ✅ |
| Background service worker | `extension/background.js` | ✅ |
| Content script (debounced) | `extension/content.js` | ✅ |
| Overlay badge CSS | `extension/styles.css` | ✅ |
| Popup settings | `extension/popup.html/js` | ✅ |
| API docs | `docs/api.md` | ✅ |

### Phase 2 — READY TO START (Tasks 16–23)
Real TRIBE v2 inference via `facebook/tribev2` + nilearn Desikan ROI mapping.
Same API contract, same extension — backend swap only.

**Start here for Phase 2:**

### Task 16 — Phase 2 dependencies
```bash
cd "/Users/kwamelaryea/Documents/Data Vault/neuro-manipulation-detector/backend"
source .venv/bin/activate
pip install -r requirements_tribe.txt
python -c "import torch, nilearn, transformers; print('phase 2 deps OK')"
```

Tasks after 16: roi.py (Task 17) → index.py (Task 18) → scorer_tribe.py (Task 19) → cache regression guard (Task 20) → flip scorer (Task 21) → smoke test (Task 22) → cross-phase integration (Task 23).

---

## Project location
`/Users/kwamelaryea/Documents/Data Vault/neuro-manipulation-detector/`

## GitHub
`https://github.com/kwamelaryea/neuro-manipulation-detector`

## Git
- Phase 1 tag: `phase-1-mvp`
- All work on `main` (merged from `feat/neuro-manipulation-detector`)

## Plan file
`/Users/kwamelaryea/Documents/Data Vault/docs/superpowers/plans/2026-06-19-neuro-manipulation-detector.md`
Tasks 16–23 = Phase 2 (TRIBE v2 backend swap)

---

## Session — 2026-06-19

### Done
- Fixed `modal.Mount` API removal (Modal 1.x) → `image.add_local_python_source()`
- Fixed `container_idle_timeout` → `scaledown_window` deprecation
- Discovered tribev2 Python code is on GitHub (`facebookresearch/tribev2`), not HF weights repo
- Added `git`, `ffmpeg` to Docker image; baked `en_core_web_lg` spaCy into image (no runtime download)
- Stored HuggingFace token as Modal secret (`huggingface` / `HF_TOKEN`) for gated LLaMA 3.2
- `modal deploy modal_tribe.py` succeeded — `nmd-tribe-scorer` live on Modal A10G
- Smoke test passed: TRIBE v2 end-to-end GPU inference working (~4 min per novel text)
- Decided **hybrid mode**: LLM default (real-time) + TRIBE v2 optional deep scan
- Added `mode: "fast" | "deep"` to `AnalyzeRequest`; `scorer: "llm" | "tribe"` to `AnalyzeResponse`
- Separate cache keys per mode; lazy imports in `scorer_tribe.py` (server starts without nilearn)
- 41/41 tests passing
- Converted Chrome extension from popup → **side panel** (MV3 `chrome.sidePanel` API)
- Side panel shows real-time fast scan + deep scan trigger/results; uses `chrome.storage.session`
- Applied ZDrive brand: violet `#6D28D9` = limbic, teal `#14B8A6` = PFC, gradient header
- Bio bars, 42px MI score, pill tags, scorer-tagged result cards

### Decisions
- **Hybrid over pure TRIBE v2**: 4 min latency too slow for real-time; LLM stays default fast path
- **Side panel over popup**: stays open across page navigations; better UX for slow deep scan
- **Limbic → violet, PFC → teal**: maps ZDrive brand colors to the two neural signals consistently
- **`NMD_USE_MODAL=true` flag**: server startup env var gates the deep scan path; no code changes needed
- **tribev2 install**: `pip install git+https://github.com/facebookresearch/tribev2` (not HF repo)

### Blockers
- **TRIBE v2 smoke test scores were inverted** (neutral Wikipedia page scored higher MI than manipulative text): root cause = texts too short (1 sentence → 5-6 segments, not enough activation variance). Real web pages (500-4000 chars) should differentiate correctly. Not fixed — needs real-world validation.
- **Whisper word extraction = 110-140s per novel text**: inherent TRIBE v2 pipeline cost (text→TTS→Whisper→brain encoding). Results cached in Modal Volume so repeated texts are fast.

### Start here next session
> Run deep scan on a real Daily Mail fear article via the side panel: start server with `NMD_USE_MODAL=true uvicorn main:app` from `backend/`, reload extension, open the side panel, scroll to trigger fast scan, then click Deep Scan — compare TRIBE v2 vs LLM MI scores to validate Phase 2.

---

## Session — 2026-06-19 (continuation)

### Done
- Fixed deep scan not returning results after 15+ min — root cause: Chrome MV3 service worker killed during 4-min Modal fetch
- Moved deep scan HTTP fetch from `background.js` to `sidepanel.js` (persistent page, no lifetime cap)
- `background.js` DEEP_ANALYZE handler now: notifies badge, stores `pendingDeepScan` in session storage, sends `DO_DEEP_SCAN` to side panel
- `sidepanel.js` runs `runDeepScan()` directly — handles fetch, result render, badge update, and error state
- `init()` picks up `pendingDeepScan` if panel opened after badge click (within 5-min window)
- `init()` sends `SCAN_NOW` to content script if no `lastResult` (panel opened before scroll)
- Fixed "Extension context invalidated" at `content.js:134` — try/catch + `chrome.runtime?.id` guard, shows "Reload page" message
- Badge "Deep Scan" button now calls `chrome.sidePanel.open({ tabId })` → side panel opens automatically on click
- Plain English labels throughout: Limbic → "Emotional pull", PFC → "Rational guard"
- MI score verdict text added: "Not manipulative" / "Moderately manipulative" / "Highly manipulative"
- Technique codes → human descriptions: `fear` → "Fear-based messaging", `tribal_identity` → "Us vs. Them framing", etc.
- "Brain signal breakdown" section label + italic sub-labels ("limbic system", "prefrontal cortex") for context
- Contrast fixes: 4 flagged elements bumped from `#4B5563` → `#6B7280` (header subtitle, section label, italic sub-labels)
- Generated glass brain icon (1024×1024 iridescent crystal, Grok) → resized to 16/32/48/128px PNGs
- Wired icon into `manifest.json` (`icons` + `action.default_icon`) and `sidepanel.html` header + waiting state
- Rebranded NMD → **ZDrive Neuro Lens** (subtitle stays "Neuro Manipulation Detector")
- 5 commits: `81f4810`, `3c7e965`, `8c78254`, `d79c360`, `4aa3db2`

### Decisions
- **Fetch in sidepanel.js, not background.js**: MV3 service workers have a hard ~5-min lifetime Chrome can enforce even with active fetch; side panel pages don't. This is the permanent architecture for any long-running request.
- **`pendingDeepScan` in session storage**: decouples badge click from panel open — panel picks up the job whenever it opens, within a 5-min freshness window
- **Plain English first, technical as sub-label**: "Emotional pull" is the label; "limbic system" is the footnote — accessible without dumbing down
- **ZDrive Neuro Lens branding**: product lives under the ZDrive family

### Blockers
- None — deep scan end-to-end working. Wikipedia confirmed: fast=0.6, TRIBE v2=0.6, both neutral ✅

### Start here next session
> Validate TRIBE v2 on manipulative content: start server with `NMD_USE_MODAL=true uvicorn main:app --reload` from `backend/`, reload extension at `chrome://extensions`, open a Daily Mail fear-based article, scroll to trigger fast scan (expect MI 7-9), open side panel, click "🔬 Deep Scan", wait ~4 min. If TRIBE v2 score matches LLM (both high), Phase 2 validation is complete.

### Context dump
- Extension commits this session: `81f4810` (SW fix) → `3c7e965` (plain English + contrast) → `8c78254` (contrast fix) → `d79c360` (glass brain icon) → `4aa3db2` (rebrand)
- Glass brain source: `extension/grok-image-a5702f70-a7c1-4953-93f1-0375de615d12.jpg` (1024×1024)
- Icon sizes: `extension/icons/icon16/32/48/128.png`
- Modal app: `https://modal.com/apps/kwame-laryea/main/deployed/nmd-tribe-scorer`
- Backend: `cd backend && source .venv/bin/activate && NMD_USE_MODAL=true uvicorn main:app --reload`
- Vault project folder: `01 - Projects/ZDrive Neuro Lens/` (execution.md created this session)
- All 41 tests still passing

### Context dump
- Modal app: `https://modal.com/apps/kwame-laryea/main/deployed/nmd-tribe-scorer`
- Modal secret name: `huggingface` / key: `HF_TOKEN` (LLaMA 3.2 access approved Jun 19)
- Model Volume: `tribe-model-cache` (TTS audio cached by text hash, Destrieux atlas downloaded)
- GitHub: `https://github.com/kwamelaryea/neuro-manipulation-detector`
- Commit: `f58ef72` — hybrid scorer + Chrome side panel with ZDrive brand
- Backend run command (fast only): `uvicorn main:app --reload`
- Backend run command (hybrid): `NMD_USE_MODAL=true uvicorn main:app --reload`
- Extension: reload at `chrome://extensions` after any JS change
