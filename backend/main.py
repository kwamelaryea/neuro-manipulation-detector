"""FastAPI app. Single /analyze endpoint, scorer-agnostic."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from cache import AnalysisCache
from models import AnalyzeRequest, AnalyzeResponse
from scorer import score_text  # active scorer (LLM in Phase 1)

app = FastAPI(title="Neuro Manipulation Detector")

# Allow the extension (any origin — extension calls from arbitrary pages).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_cache = AnalysisCache()


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/analyze", response_model=AnalyzeResponse)
def analyze(req: AnalyzeRequest) -> AnalyzeResponse:
    cached = _cache.get(req.text)
    if cached is not None:
        return cached
    result = score_text(req.text)
    _cache.set(req.text, result)
    return result
