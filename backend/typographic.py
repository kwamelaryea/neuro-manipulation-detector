"""Typographic arousal features — catches what TRIBE v2's TTS pipeline flattens.

TRIBE v2 converts text→speech before neural inference, so ALL-CAPS,
exclamation marks, and urgency keywords lose their visual/typographic
intensity. This module scores those surface-level manipulation signals
as a separate feature to blend with the neural MI.

Returns a float 0.0–1.0 representing typographic arousal intensity.
"""
import re

URGENCY_WORDS = frozenset({
    "now", "immediately", "urgent", "hurry", "rush", "fast",
    "quick", "limited", "expires", "deadline", "last", "final",
    "act", "don't wait", "before it's too late", "running out",
    "only", "exclusive", "breaking", "alert", "warning",
})

FEAR_WORDS = frozenset({
    "die", "death", "kill", "fatal", "danger", "threat",
    "destroy", "collapse", "crash", "crisis", "catastrophe",
    "devastating", "victim", "suffer", "worst", "terrifying",
    "horrifying", "nightmare", "emergency", "panic",
})

FOMO_WORDS = frozenset({
    "miss", "missing", "left behind", "everyone", "thousands",
    "millions", "already", "don't be", "losing", "lost",
    "too late", "while you can", "before",
})


def typographic_score(text: str) -> float:
    """Score typographic manipulation signals from 0.0 to 1.0."""
    if not text or len(text) < 10:
        return 0.0

    words = text.split()
    n_words = max(len(words), 1)
    text_lower = text.lower()

    caps_ratio = sum(1 for w in words if w.isupper() and len(w) > 1) / n_words
    exclamation_density = text.count("!") / n_words
    question_density = text.count("?") / n_words

    urgency_hits = sum(1 for w in URGENCY_WORDS if w in text_lower) / max(len(URGENCY_WORDS), 1)
    fear_hits = sum(1 for w in FEAR_WORDS if w in text_lower) / max(len(FEAR_WORDS), 1)
    fomo_hits = sum(1 for w in FOMO_WORDS if w in text_lower) / max(len(FOMO_WORDS), 1)

    scores = [
        min(1.0, caps_ratio * 5.0),
        min(1.0, exclamation_density * 10.0),
        min(1.0, (question_density * 8.0) * 0.3),
        min(1.0, urgency_hits * 4.0),
        min(1.0, fear_hits * 5.0),
        min(1.0, fomo_hits * 4.0),
    ]

    return min(1.0, sum(scores) / len(scores) * 2.0)
