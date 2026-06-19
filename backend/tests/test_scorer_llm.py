from scorer_llm import SYSTEM_PROMPT


def test_prompt_encodes_tribe_framework():
    p = SYSTEM_PROMPT.lower()
    # Core neuro framework must be present.
    assert "limbic" in p
    assert "amygdala" in p
    assert "insula" in p
    assert "prefrontal" in p or "pfc" in p
    assert "dlpfc" in p
    assert "acc" in p
    assert "manipulation index" in p


def test_prompt_specifies_output_fields():
    p = SYSTEM_PROMPT
    for field in (
        "limbic_score",
        "pfc_score",
        "manipulation_index",
        "dominant_technique",
        "confidence",
    ):
        assert field in p


def test_prompt_lists_all_techniques():
    p = SYSTEM_PROMPT
    for tech in ("fear", "urgency", "tribal_identity", "reward_loop", "neutral"):
        assert tech in p


def test_prompt_specifies_manipulation_index_formula():
    p = SYSTEM_PROMPT.lower()
    # The ratio rationale: limbic / (pfc + epsilon)
    assert "limbic" in p and "pfc" in p
    assert "ratio" in p or "/" in SYSTEM_PROMPT


import json
from unittest.mock import MagicMock, patch

from models import AnalyzeResponse
from scorer_llm import score_text


def _fake_message(payload: dict):
    """Build a fake anthropic Message with one text block containing JSON."""
    block = MagicMock()
    block.type = "text"
    block.text = json.dumps(payload)
    msg = MagicMock()
    msg.content = [block]
    return msg


def test_score_text_returns_analyze_response():
    payload = {
        "limbic_score": 0.85,
        "pfc_score": 0.15,
        "manipulation_index": 8.1,
        "dominant_technique": "fear",
        "confidence": "high",
    }
    with patch("scorer_llm._client") as client:
        client.messages.create.return_value = _fake_message(payload)
        result = score_text("The end is near! Act before it's too late!")

    assert isinstance(result, AnalyzeResponse)
    assert result.dominant_technique == "fear"
    assert result.manipulation_index == 8.1


def test_score_text_calls_model_sonnet_4_6():
    payload = {
        "limbic_score": 0.1,
        "pfc_score": 0.8,
        "manipulation_index": 1.0,
        "dominant_technique": "neutral",
        "confidence": "high",
    }
    with patch("scorer_llm._client") as client:
        client.messages.create.return_value = _fake_message(payload)
        score_text("The meeting is scheduled for 3pm on Tuesday.")
        kwargs = client.messages.create.call_args.kwargs
        assert kwargs["model"] == "claude-sonnet-4-6"
        assert kwargs["system"]  # system prompt passed
