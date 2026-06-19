from index import compute_scores
from models import AnalyzeResponse


def test_high_limbic_low_pfc_is_high_manipulation():
    roi = {
        "insula": 0.9, "entorhinal": 0.8, "parahippocampal": 0.85,
        "rostralmiddlefrontal": 0.1, "caudalanteriorcingulate": 0.1, "rostralanteriorcingulate": 0.1,
    }
    out = compute_scores(roi, text_len=600)
    assert isinstance(out, AnalyzeResponse)
    assert out.limbic_score > 0.7
    assert out.pfc_score < 0.3
    assert out.manipulation_index > 6.0


def test_balanced_is_low_manipulation():
    roi = {
        "insula": 0.3, "entorhinal": 0.3, "parahippocampal": 0.3,
        "rostralmiddlefrontal": 0.6, "caudalanteriorcingulate": 0.55, "rostralanteriorcingulate": 0.6,
    }
    out = compute_scores(roi, text_len=600)
    assert out.manipulation_index < 5.0  # 10*0.3/(0.583+0.1) ≈ 4.39


def test_confidence_low_for_short_text():
    roi = {
        "insula": 0.5, "entorhinal": 0.5, "parahippocampal": 0.5,
        "rostralmiddlefrontal": 0.5, "caudalanteriorcingulate": 0.5, "rostralanteriorcingulate": 0.5,
    }
    out = compute_scores(roi, text_len=20)
    assert out.confidence == "low"


def test_neutral_technique_when_pfc_dominant():
    roi = {
        "insula": 0.2, "entorhinal": 0.2, "parahippocampal": 0.2,
        "rostralmiddlefrontal": 0.7, "caudalanteriorcingulate": 0.6, "rostralanteriorcingulate": 0.65,
    }
    out = compute_scores(roi, text_len=400)
    assert out.dominant_technique == "neutral"


def test_manipulation_index_clamped_to_10():
    roi = {
        "insula": 1.0, "entorhinal": 1.0, "parahippocampal": 1.0,
        "rostralmiddlefrontal": 0.0, "caudalanteriorcingulate": 0.0, "rostralanteriorcingulate": 0.0,
    }
    out = compute_scores(roi, text_len=500)
    assert out.manipulation_index <= 10.0
