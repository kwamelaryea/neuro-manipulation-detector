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
