"""API contract — frozen across Phase 1 (LLM) and Phase 2 (TRIBE v2).

Both scorers MUST return an AnalyzeResponse. The Chrome extension consumes
this exact shape and never changes between phases.
"""
from typing import Literal, Optional

from pydantic import BaseModel, Field

DOMINANT_TECHNIQUES = ("fear", "urgency", "tribal_identity", "reward_loop", "neutral")
CONFIDENCE_LEVELS = ("low", "medium", "high")

TechniqueType = Literal["fear", "urgency", "tribal_identity", "reward_loop", "neutral"]
ConfidenceType = Literal["low", "medium", "high"]


class AnalyzeRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Visible text extracted from the page")
    url: Optional[str] = Field(None, description="Source URL (metadata only, not scored)")
    mode: Literal["fast", "deep"] = Field("fast", description="fast=LLM scorer, deep=TRIBE v2 via Modal")


class AnalyzeResponse(BaseModel):
    limbic_score: float = Field(..., ge=0.0, le=1.0, description="Emotional arousal signal")
    pfc_score: float = Field(..., ge=0.0, le=1.0, description="Cognitive engagement / suppression signal")
    manipulation_index: float = Field(..., ge=0.0, le=10.0, description="Ratio-based composite")
    dominant_technique: TechniqueType = Field(..., description="Primary persuasion technique detected")
    confidence: ConfidenceType = Field(..., description="Scorer confidence band")
    scorer: Optional[Literal["llm", "tribe"]] = Field(None, description="Which scorer produced this result")
