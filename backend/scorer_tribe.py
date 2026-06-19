"""Phase 2 scorer: TRIBE v2 neural inference."""

from models import AnalyzeResponse
from index import compute_scores
from roi import get_roi_vertex_indices, roi_means
import numpy as np
import tempfile
import os

_MODEL = None


def _run_tribe(text: str) -> np.ndarray:
    global _MODEL
    if _MODEL is None:
        # Lazy import — tribev2 is heavy and not installed in Phase 1 / test envs
        from tribev2 import TribeModel  # noqa: PLC0415
        _MODEL = TribeModel.from_pretrained("facebook/tribev2", cache_folder="./cache")

    # Write to temp file and close before model reads — flush required on macOS
    temp_file = tempfile.NamedTemporaryFile(suffix=".txt", delete=False, mode="w", encoding="utf-8")
    temp_path = temp_file.name
    temp_file.write(text)
    temp_file.close()

    try:
        df = _MODEL.get_events_dataframe(text_path=temp_path)
        preds, segments = _MODEL.predict(events=df)
        return np.asarray(preds)
    finally:
        os.unlink(temp_path)


def score_text(text: str) -> AnalyzeResponse:
    acts = _run_tribe(text)
    idx = get_roi_vertex_indices()
    means = roi_means(acts, idx)
    return compute_scores(means, text_len=len(text))
