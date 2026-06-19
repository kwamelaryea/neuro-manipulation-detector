# Neuro Manipulation Detector

A Chrome extension + FastAPI backend that scans visible web page text and shows an overlay badge reporting neural/emotional manipulation scores in real-time.

The detector identifies persuasion techniques designed to bypass deliberate reasoning — fear appeals, urgency tactics, tribal identity framing, and reward-loop engineering — by scoring the balance between limbic arousal (emotional trigger) and prefrontal engagement (cognitive reflection).

## How It Works

**Phase 1 (Current — `phase-1-mvp`):** Claude Sonnet 4.6 acts as a TRIBE v2 conceptual proxy. The system prompt encodes Meta FAIR's TRIBE v2 brain-encoding framework as a scoring rubric. No neural inference; pure reasoning about what cortical/limbic response the text is designed to evoke.

**Scoring Formula:**
```
manipulation_index = 10 * limbic_score / (pfc_score + 0.1)
```
High limbic + low PFC = high manipulation. Balanced or PFC-dominant content = low manipulation.

**Response Shape:**
```json
{
  "limbic_score": 0.0,
  "pfc_score": 0.0,
  "manipulation_index": 0.0,
  "dominant_technique": "fear|urgency|tribal_identity|reward_loop|neutral",
  "confidence": "low|medium|high"
}
```

## Quick Start

### Backend

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export ANTHROPIC_API_KEY=<your-key>
uvicorn main:app --port 8000
```

Endpoints:
- `GET /health` — liveness check
- `POST /analyze` — body: `{"text": "...", "url": "..."}` (url optional)

### Extension

1. Open `chrome://extensions/`
2. Enable **Developer mode**
3. Click **Load unpacked** → select the `extension/` folder
4. Visit any website; text is scanned as you scroll
5. Badge appears bottom-right; click to expand the full score card

All traffic stays local — the extension calls `http://localhost:8000` only.

## Live Test Results

E2E verified 2026-06-19 (Task 15):

| Site | Manipulation | Limbic | PFC | Technique | Confidence |
|---|---|---|---|---|---|
| Daily Mail homepage | 8.0 | 82% | 17% | fear | medium |
| Daily Mail article | 8.0 | 82% | 17% | fear | medium |
| Wikipedia (World Cup) | 0.6 | 5% | 75% | neutral | high |

Tabloid layout + sensational copy triggers amygdala-dominant response. Wikipedia invites dlPFC-dominant reflection.

## Phase 1 vs Phase 2

| | Phase 1 | Phase 2 |
|---|---|---|
| Scorer | Claude Sonnet 4.6 (LLM reasoning) | `facebook/tribev2` (neural inference) |
| Speed | ~1–2s (API latency) | ~5–10s (GPU, cold model load) |
| Interpretability | Explainable via prompt rubric | Opaque (vertex activations → ROI aggregation) |
| Accuracy | Conceptual proxy | Empirical (fMRI-validated encoding model) |
| API contract | `AnalyzeResponse` | Identical — extension unchanged |

Both phases return the same frozen contract. The extension is phase-agnostic.

## Running Tests

```bash
cd backend
source .venv/bin/activate
pytest -q
# 28 passed
```

Coverage: API contract validation, SHA256 cache, scorer interface, FastAPI endpoint, CORS, cache deduplication.

## Project Structure

```
├── backend/
│   ├── main.py           # FastAPI /analyze endpoint
│   ├── models.py         # Frozen API contract (AnalyzeRequest/Response)
│   ├── scorer_llm.py     # Claude proxy + TRIBE v2 system prompt
│   ├── scorer.py         # Scorer shim (one-line phase swap)
│   ├── cache.py          # SHA256-keyed memory + disk cache
│   ├── requirements.txt  # Phase 1 deps
│   └── tests/            # 28 tests
├── extension/
│   ├── manifest.json     # MV3 config
│   ├── background.js     # Service worker
│   ├── content.js        # Debounced text extraction + badge render
│   ├── popup.html/js     # Settings (backend URL, on/off toggle)
│   └── styles.css        # Overlay badge (dark, accessible contrast)
├── docs/
│   └── api.md            # Full API documentation
└── HANDOFF.md            # Phase status and next steps
```

## Stack

- **Backend:** Python 3.12, FastAPI, Anthropic SDK, Pydantic, pytest
- **Extension:** Vanilla JS (MV3), no framework
- **Cache:** SHA256-indexed JSON on disk

## Phase 2

Swaps the LLM scorer for real `facebook/tribev2` inference + nilearn Desikan atlas ROI mapping. The API contract and extension are untouched. See `HANDOFF.md` for the task breakdown (Tasks 16–23).

## License

MIT
