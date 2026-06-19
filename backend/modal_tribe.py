"""Modal serverless GPU wrapper for TRIBE v2 inference.

Deploys to Modal A10G. Model weights cached in a Modal Volume so they
download once and persist across cold starts.

Deploy:    modal deploy backend/modal_tribe.py
Smoke test: modal run backend/modal_tribe.py
"""
import sys
from pathlib import Path

import modal

app = modal.App("nmd-tribe-scorer")

# Modal Volume: weights persist across container restarts (~multi-GB, download once)
model_cache = modal.Volume.from_name("tribe-model-cache", create_if_missing=True)

# Mount local backend Python modules so roi.py / index.py / models.py are available
backend_mount = modal.Mount.from_local_dir(
    Path(__file__).parent,
    remote_path="/backend",
    condition=lambda path: (
        path.suffix == ".py"
        and not path.name.startswith("test_")
        and path.name not in ("modal_tribe.py", "conftest.py")
    ),
)

image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install(
        "numpy==2.2.1",
        "nilearn==0.11.1",
        "nibabel==5.3.2",
        "pydantic==2.10.4",
        "fastapi==0.115.6",
    )
    .run_commands("pip install git+https://huggingface.co/facebook/tribev2")
)


@app.cls(
    image=image,
    gpu="A10G",
    mounts=[backend_mount],
    volumes={"/cache": model_cache},
    container_idle_timeout=1200,  # keep warm 20 min between requests
    timeout=120,
)
class TribeScorer:
    @modal.enter()
    def load(self):
        """Runs once per container — loads model + atlas into GPU memory."""
        sys.path.insert(0, "/backend")

        from tribev2 import TribeModel
        from roi import get_roi_vertex_indices

        self._model = TribeModel.from_pretrained(
            "facebook/tribev2",
            cache_folder="/cache",
        )
        # Pre-load Destrieux atlas (downloads once, then cached in volume)
        self._roi_idx = get_roi_vertex_indices()

    @modal.method()
    def score(self, text: str) -> dict:
        """TRIBE v2 inference on text. Returns AnalyzeResponse fields as dict."""
        import os
        import tempfile

        import numpy as np

        from index import compute_scores
        from roi import roi_means

        tf = tempfile.NamedTemporaryFile(
            suffix=".txt", delete=False, mode="w", encoding="utf-8"
        )
        tf.write(text)
        tf.close()

        try:
            df = self._model.get_events_dataframe(text_path=tf.name)
            preds, _ = self._model.predict(events=df)
            acts = np.asarray(preds)
        finally:
            os.unlink(tf.name)

        means = roi_means(acts, self._roi_idx)
        result = compute_scores(means, text_len=len(text))
        return result.model_dump()


@app.local_entrypoint()
def main():
    """Quick smoke test: modal run backend/modal_tribe.py"""
    scorer = TribeScorer()

    manipulative = "WARNING: Your account will be DELETED in 24 hours unless you act NOW!"
    neutral = "The committee meets quarterly to review audited financial statements."

    for text, label in [(manipulative, "manipulative"), (neutral, "neutral")]:
        result = scorer.score.remote(text)
        print(f"\n[{label}]")
        for k, v in result.items():
            print(f"  {k}: {v}")
