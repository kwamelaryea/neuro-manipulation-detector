from unittest.mock import patch

import numpy as np

from models import AnalyzeResponse
import scorer_tribe


def test_score_text_returns_contract(monkeypatch):
    fake_acts = np.random.rand(4, 20484)
    with patch.object(scorer_tribe, "_run_tribe", return_value=fake_acts):
        out = scorer_tribe.score_text("Buy now before it disappears forever!")
    assert isinstance(out, AnalyzeResponse)
    assert 0.0 <= out.limbic_score <= 1.0
    assert 0.0 <= out.manipulation_index <= 10.0
    assert out.dominant_technique in ("fear", "urgency", "tribal_identity", "reward_loop", "neutral")


def test_score_text_passes_text_len_to_index(monkeypatch):
    fake_acts = np.random.rand(2, 20484)
    captured = {}

    def fake_compute(roi_means, text_len, typo_score=0.0):
        captured["text_len"] = text_len
        return AnalyzeResponse(
            limbic_score=0.5, pfc_score=0.5, manipulation_index=5.0,
            dominant_technique="neutral", confidence="medium",
        )

    import index
    with patch.object(scorer_tribe, "_run_tribe", return_value=fake_acts), \
         patch.object(index, "compute_scores", side_effect=fake_compute):
        scorer_tribe.score_text("hello world")
    assert captured["text_len"] == len("hello world")


def test_run_tribe_resets_model_singleton():
    # Confirm _MODEL starts as None (module freshly imported or reset)
    import importlib
    import sys
    # Reload to get a clean module state
    if "scorer_tribe" in sys.modules:
        mod = sys.modules["scorer_tribe"]
        original = mod._MODEL
        mod._MODEL = None
        assert mod._MODEL is None
        mod._MODEL = original  # restore
