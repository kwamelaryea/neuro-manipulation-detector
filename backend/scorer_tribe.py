"""Phase 2 scorer: TRIBE v2 neural inference.

Two execution paths:
  NMD_USE_MODAL=true  → delegates to Modal A10G (production)
  default             → runs _run_tribe() locally (requires GPU + tribev2 installed)

Tests mock _run_tribe() directly; the Modal path is not exercised in unit tests.
"""
import os

from models import AnalyzeResponse

_USE_MODAL = os.getenv("NMD_USE_MODAL", "false").lower() == "true"

_MODEL = None


def _run_tribe(text: str) -> "np.ndarray":
    """Local TRIBE v2 inference. Mocked in unit tests; real path needs GPU."""
    import numpy as np  # noqa: PLC0415

    global _MODEL
    if _MODEL is None:
        # Lazy import — tribev2 not installed in Phase 1 / test envs
        from tribev2 import TribeModel  # noqa: PLC0415
        _MODEL = TribeModel.from_pretrained("facebook/tribev2", cache_folder="./cache")

    # File path required — model converts text to speech internally
    import tempfile, os as _os  # noqa: E401
    tf = tempfile.NamedTemporaryFile(suffix=".txt", delete=False, mode="w", encoding="utf-8")
    tf.write(text)
    tf.close()
    try:
        df = _MODEL.get_events_dataframe(text_path=tf.name)
        preds, _ = _MODEL.predict(events=df)
        return np.asarray(preds)
    finally:
        _os.unlink(tf.name)


def score_text(text: str) -> AnalyzeResponse:
    if _USE_MODAL:
        # Modal 1.x: use Cls.from_name to look up the deployed app instance.
        # Importing TribeScorer directly from modal_tribe.py gives an unhydrated
        # class that can't call .remote() outside of a Modal run context.
        import modal
        TribeScorer = modal.Cls.from_name("nmd-tribe-scorer", "TribeScorer")
        scorer = TribeScorer()
        result = scorer.score.remote(text)
        return AnalyzeResponse(**result)

    # Local path — needs tribev2, nilearn, GPU installed.
    import numpy as np
    from roi import get_roi_vertex_indices, roi_means
    from index import compute_scores
    from typographic import typographic_score

    acts = _run_tribe(text)
    idx = get_roi_vertex_indices()
    typo = typographic_score(text)
    means = roi_means(acts, idx)
    return compute_scores(means, text_len=len(text), typo_score=typo)
