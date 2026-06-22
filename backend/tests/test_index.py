"""Tests for the z-contrast MI formula and technique classifier.

ROI values here are z-scores (can be negative, unbounded) — NOT [0,1].
Positive z = more active than neutral baseline.
"""
from index import compute_scores
from models import AnalyzeResponse


def _roi(emotional_z=0.0, control_z=0.0):
    """Helper: set all emotional ROIs to one z-value, all control to another."""
    return {
        "insula": emotional_z, "tpj": emotional_z,
        "mtg": emotional_z, "parahippocampal": emotional_z,
        "broca45": control_z, "sts": control_z,
        "dlpfc": control_z, "acc": control_z,
    }


def test_high_emotional_low_control_is_high_mi():
    out = compute_scores(_roi(emotional_z=1.5, control_z=-0.5), text_len=600)
    assert isinstance(out, AnalyzeResponse)
    assert out.manipulation_index > 8.0


def test_neutral_baseline_is_low_mi():
    out = compute_scores(_roi(emotional_z=0.0, control_z=0.0), text_len=600)
    assert out.manipulation_index < 4.0


def test_control_dominant_is_low_mi():
    out = compute_scores(_roi(emotional_z=-0.5, control_z=1.0), text_len=600)
    assert out.manipulation_index < 2.0


def test_neutral_technique_when_mi_low():
    out = compute_scores(_roi(emotional_z=-0.2, control_z=0.3), text_len=400)
    assert out.dominant_technique == "neutral"


def test_manipulation_index_clamped_to_10():
    out = compute_scores(_roi(emotional_z=5.0, control_z=-5.0), text_len=500)
    assert out.manipulation_index <= 10.0


def test_manipulation_index_clamped_to_0():
    out = compute_scores(_roi(emotional_z=-5.0, control_z=5.0), text_len=500)
    assert out.manipulation_index >= 0.0


def test_confidence_low_for_short_text():
    out = compute_scores(_roi(), text_len=20)
    assert out.confidence == "low"


def test_confidence_high_for_long_text():
    out = compute_scores(_roi(), text_len=600)
    assert out.confidence == "high"


def test_roi_detail_has_all_keys():
    out = compute_scores(_roi(0.5, -0.3), text_len=300)
    expected_keys = {"insula", "tpj", "mtg", "parahippocampal", "broca45", "sts", "dlpfc", "acc"}
    assert set(out.roi_detail.keys()) == expected_keys


def test_roi_detail_values_in_unit_range():
    out = compute_scores(_roi(1.0, -1.0), text_len=300)
    for v in out.roi_detail.values():
        assert 0.0 <= v <= 1.0
