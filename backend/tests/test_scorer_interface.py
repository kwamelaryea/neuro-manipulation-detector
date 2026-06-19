import scorer


def test_scorer_exposes_score_text():
    assert hasattr(scorer, "score_text")
    assert callable(scorer.score_text)


def test_scorer_active_backend_is_llm_in_phase1():
    assert scorer.ACTIVE_BACKEND == "llm"
