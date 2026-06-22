"""FastAPI app — hybrid scorer endpoint.

mode=fast (default): LLM scorer, ~1-2s latency.
mode=deep:           TRIBE v2 via Modal A10G, ~3-4 min latency.
                     Requires NMD_USE_MODAL=true at server startup.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from cache import AnalysisCache
from models import AnalyzeRequest, AnalyzeResponse
from scorer_llm import score_text as _score_fast

app = FastAPI(title="Neuro Manipulation Detector")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_cache = AnalysisCache()


def _score_deep(text: str) -> AnalyzeResponse:
    # Lazy import — avoids nilearn/Modal at startup when only fast mode is used.
    from scorer_tribe import score_text
    return score_text(text)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/analyze", response_model=AnalyzeResponse)
def analyze(req: AnalyzeRequest) -> AnalyzeResponse:
    cache_key = f"{req.mode}:{req.text}"
    cached = _cache.get(cache_key)
    if cached is not None:
        return cached

    if req.mode == "deep":
        try:
            text = req.text[:3000]
            result = _score_deep(text)
            result.scorer = "tribe"
        except Exception as exc:
            # TRIBE v2 unavailable (tribev2 not installed / Modal not configured).
            # Fall back to LLM and surface the correct scorer label so the
            # extension can show "LLM fallback" instead of "TRIBE v2".
            import logging
            logging.warning("TRIBE v2 failed (%s), falling back to LLM scorer", exc)
            result = _score_fast(req.text)
            result.scorer = "llm"
    else:
        result = _score_fast(req.text)
        result.scorer = "llm"

    _cache.set(cache_key, result)
    return result
