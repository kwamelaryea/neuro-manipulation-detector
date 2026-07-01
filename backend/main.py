"""FastAPI app — hybrid scorer endpoint.

mode=fast (default): LLM scorer, ~1-2s latency.
mode=deep:           TRIBE v2 via Modal A10G, ~3-4 min latency.
                     Requires NMD_USE_MODAL=true at server startup.
"""
import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from cache import AnalysisCache
from models import AnalyzeRequest, AnalyzeResponse
from scorer_llm import score_text as _score_fast

INTERNAL_KEY = os.environ.get("INTERNAL_SERVICE_KEY", "")

app = FastAPI(title="Neuro Manipulation Detector")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["chrome-extension://*", "https://zdrive-neuro-lens.kwame-laryea.workers.dev"],
    allow_origin_regex=r"^chrome-extension://.*$",
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["Content-Type", "X-ZDrive-API-Key"],
)


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    if request.url.path == "/health" or request.method == "OPTIONS":
        return await call_next(request)
    key = request.headers.get("X-ZDrive-API-Key", "")
    if INTERNAL_KEY and key == INTERNAL_KEY:
        return await call_next(request)
    if key.startswith("znl_") and len(key) >= 16:
        return await call_next(request)
    # Auth middleware runs before CORSMiddleware in the stack, so we must add
    # CORS headers manually here — otherwise the browser sees a cross-origin
    # 401 with no Access-Control-Allow-Origin and throws "TypeError: Failed to fetch"
    # instead of surfacing the real auth error.
    origin = request.headers.get("origin", "")
    cors_headers = {}
    if origin:
        cors_headers["Access-Control-Allow-Origin"] = origin
        cors_headers["Access-Control-Allow-Headers"] = "Content-Type, X-ZDrive-API-Key"
        cors_headers["Vary"] = "Origin"
    return JSONResponse({"error": "Invalid or missing X-ZDrive-API-Key. Get your key at zdrive.io."}, status_code=401, headers=cors_headers)

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
