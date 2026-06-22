"""Convert ROI means into the frozen AnalyzeResponse contract."""
from roi import LIMBIC_ROIS, PFC_ROIS
from models import AnalyzeResponse

EPSILON = 0.1


def _avg(roi_means: dict[str, float], rois: tuple[str, ...]) -> float:
    vals = [roi_means.get(r, 0.0) for r in rois]
    return sum(vals) / len(vals) if vals else 0.0


def _technique(roi_means: dict[str, float]) -> str:
    insula = roi_means.get("insula", 0.0)
    entorhinal = roi_means.get("entorhinal", 0.0)
    parahip = roi_means.get("parahippocampal", 0.0)
    limbic = _avg(roi_means, LIMBIC_ROIS)
    pfc = _avg(roi_means, PFC_ROIS)

    if limbic < 0.35 and pfc >= 0.4:
        return "neutral"
    if insula >= max(entorhinal, parahip) and insula > 0.6:
        return "urgency"
    if (entorhinal + parahip) / 2 > insula:
        return "tribal_identity"
    if insula > 0.5 and pfc < 0.3:
        return "reward_loop"
    return "fear"


def _confidence(text_len: int) -> str:
    if text_len < 60:
        return "low"
    if text_len < 300:
        return "medium"
    return "high"


def compute_scores(roi_means: dict[str, float], text_len: int) -> AnalyzeResponse:
    limbic = _avg(roi_means, LIMBIC_ROIS)
    pfc = _avg(roi_means, PFC_ROIS)
    mi = 10.0 * limbic / (pfc + EPSILON)
    mi = max(0.0, min(10.0, mi))
    return AnalyzeResponse(
        limbic_score=round(limbic, 4),
        pfc_score=round(pfc, 4),
        manipulation_index=round(mi, 2),
        dominant_technique=_technique(roi_means),
        confidence=_confidence(text_len),
        roi_detail={k: round(v, 4) for k, v in roi_means.items()},
    )
