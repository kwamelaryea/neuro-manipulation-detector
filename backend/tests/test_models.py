import pytest
from pydantic import ValidationError

from models import AnalyzeRequest, AnalyzeResponse, DOMINANT_TECHNIQUES, CONFIDENCE_LEVELS


def test_request_requires_text():
    req = AnalyzeRequest(text="Buy now before it's gone forever!")
    assert req.text == "Buy now before it's gone forever!"
    assert req.url is None  # url is optional metadata


def test_request_rejects_empty_text():
    with pytest.raises(ValidationError):
        AnalyzeRequest(text="")


def test_request_accepts_optional_url():
    req = AnalyzeRequest(text="hello", url="https://example.com")
    assert req.url == "https://example.com"


def test_response_shape_and_bounds():
    resp = AnalyzeResponse(
        limbic_score=0.82,
        pfc_score=0.20,
        manipulation_index=7.3,
        dominant_technique="fear",
        confidence="high",
    )
    assert 0.0 <= resp.limbic_score <= 1.0
    assert 0.0 <= resp.pfc_score <= 1.0
    assert 0.0 <= resp.manipulation_index <= 10.0
    assert resp.dominant_technique in DOMINANT_TECHNIQUES
    assert resp.confidence in CONFIDENCE_LEVELS


def test_response_rejects_out_of_range_scores():
    with pytest.raises(ValidationError):
        AnalyzeResponse(
            limbic_score=1.5,  # > 1.0
            pfc_score=0.2,
            manipulation_index=5.0,
            dominant_technique="fear",
            confidence="high",
        )


def test_response_rejects_unknown_technique():
    with pytest.raises(ValidationError):
        AnalyzeResponse(
            limbic_score=0.5,
            pfc_score=0.5,
            manipulation_index=5.0,
            dominant_technique="hypnosis",  # not in enum
            confidence="medium",
        )


def test_constants_are_exact():
    assert DOMINANT_TECHNIQUES == (
        "fear",
        "urgency",
        "tribal_identity",
        "reward_loop",
        "neutral",
    )
    assert CONFIDENCE_LEVELS == ("low", "medium", "high")
