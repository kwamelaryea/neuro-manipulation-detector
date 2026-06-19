# Neuro Manipulation Detector — Handoff

## Status: Phase 1 COMPLETE ✅ — Phase 2 ready to start

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
