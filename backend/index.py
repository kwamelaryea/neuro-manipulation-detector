"""Convert ROI z-scores into the AnalyzeResponse contract.

MI calibration v3 (2026-06-22): z-scored contrast formula.
ROI z-scores are relative to a neutral population baseline — positive
means this text activates the region more than neutral text.

MI = sigmoid(emotional_z - control_z) scaled to 0-10.
  emotional_z: mean z across insula, TPJ, MTG, parahippocampal
  control_z:   mean z across Broca45, STS, dlPFC, ACC

A neutral text yields z ≈ 0 in all regions → MI ≈ 5 * sigmoid(0) = 5.
To shift the neutral midpoint to ~2, we subtract a bias.
"""
import math

from roi import EMOTIONAL_ROIS, CONTROL_ROIS
from models import AnalyzeResponse

INTENSITY_SCALE = 3.0
INTENSITY_SHIFT = 0.2
CONTRAST_WEIGHT = 2.0


def _avg(roi_means: dict[str, float], rois: tuple[str, ...]) -> float:
    vals = [roi_means.get(r, 0.0) for r in rois]
    return sum(vals) / len(vals) if vals else 0.0


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def _technique(roi_means: dict[str, float], mi: float) -> str:
    if mi < 4.0:
        return "neutral"

    insula = roi_means.get("insula", 0.0)
    tpj = roi_means.get("tpj", 0.0)
    mtg = roi_means.get("mtg", 0.0)
    emotional = _avg(roi_means, EMOTIONAL_ROIS)

    if insula > max(tpj, mtg) and insula > emotional:
        return "urgency"
    if tpj > insula and tpj > mtg:
        return "tribal_identity"
    if mtg > insula:
        return "reward_loop"
    return "fear"


def _confidence(text_len: int) -> str:
    if text_len < 60:
        return "low"
    if text_len < 300:
        return "medium"
    return "high"


def _squash_to_unit(z: float) -> float:
    """Map z-score to [0,1] for AnalyzeResponse display."""
    return max(0.0, min(1.0, _sigmoid(z)))


def compute_scores(roi_means: dict[str, float], text_len: int) -> AnalyzeResponse:
    emotional_z = _avg(roi_means, EMOTIONAL_ROIS)
    control_z = _avg(roi_means, CONTROL_ROIS)

    overall_z = (emotional_z + control_z) / 2.0
    contrast = emotional_z - control_z
    mi = 10.0 * _sigmoid(
        INTENSITY_SCALE * (overall_z - INTENSITY_SHIFT)
        + CONTRAST_WEIGHT * contrast
    )
    mi = max(0.0, min(10.0, round(mi, 2)))

    limbic_display = _squash_to_unit(emotional_z)
    pfc_display = _squash_to_unit(control_z)

    return AnalyzeResponse(
        limbic_score=round(limbic_display, 4),
        pfc_score=round(pfc_display, 4),
        manipulation_index=mi,
        dominant_technique=_technique(roi_means, mi),
        confidence=_confidence(text_len),
        roi_detail={k: round(_squash_to_unit(v), 4) for k, v in roi_means.items()},
    )
