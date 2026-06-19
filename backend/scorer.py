"""Active-scorer indirection.

Phase 1: re-export the LLM scorer.
Phase 2: change the import below to `from scorer_tribe import score_text`
         and set ACTIVE_BACKEND = "tribe". Nothing else in the app changes.
"""
from scorer_llm import score_text  # noqa: F401

ACTIVE_BACKEND = "llm"
