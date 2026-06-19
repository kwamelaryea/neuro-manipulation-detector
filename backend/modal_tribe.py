"""Modal serverless GPU wrapper for TRIBE v2 inference.

Deploys to Modal A10G. Model weights cached in a Modal Volume so they
download once and persist across cold starts.

Deploy:    modal deploy modal_tribe.py          (run from backend/)
Smoke test: modal run modal_tribe.py            (run from backend/)

Prerequisites:
  1. Create a HuggingFace token with LLaMA 3.2-3B access at hf.co/settings/tokens
  2. Store it as a Modal secret: modal secret create huggingface HF_TOKEN=hf_...
  3. Request LLaMA 3.2 access at hf.co/meta-llama/Llama-3.2-3B (free, auto-approved)
"""
import modal

app = modal.App("nmd-tribe-scorer")

# Modal Volume: weights persist across container restarts (~multi-GB, download once)
model_cache = modal.Volume.from_name("tribe-model-cache", create_if_missing=True)

# HF token needed for gated LLaMA 3.2-3B (text encoder inside TRIBE v2)
hf_secret = modal.Secret.from_name("huggingface")

# Build image — code from GitHub, weights from HuggingFace at runtime
image = (
    modal.Image.debian_slim(python_version="3.12")
    .apt_install("git", "ffmpeg")  # ffmpeg required for TTS audio processing
    .pip_install(
        "numpy==2.2.1",
        "nilearn==0.11.1",
        "nibabel==5.3.2",
        "pydantic==2.10.4",
        "fastapi==0.115.6",
    )
    # tribev2 Python package lives on GitHub, not HuggingFace
    .run_commands(
        "pip install git+https://github.com/facebookresearch/tribev2",
        # spaCy NLP model required for word extraction — bake in to avoid runtime download
        "python -m spacy download en_core_web_lg",
    )
    # Copy local backend modules into the image (roi, index, models, cache)
    .add_local_python_source("roi", "index", "models", "cache")
)


@app.cls(
    image=image,
    gpu="A10G",
    volumes={"/cache": model_cache},
    secrets=[hf_secret],
    scaledown_window=1200,  # keep warm 20 min between requests
    # Whisper word extraction + TRIBE inference takes 2-4 min on cold text
    timeout=600,
)
class TribeScorer:
    @modal.enter()
    def load(self):
        """Runs once per container — loads model + atlas into GPU memory."""
        import os
        from tribev2 import TribeModel
        from roi import get_roi_vertex_indices

        # Authenticate with HuggingFace for gated LLaMA 3.2 text encoder
        hf_token = os.environ.get("HF_TOKEN")
        if hf_token:
            from huggingface_hub import login
            login(token=hf_token, add_to_git_credential=False)

        # /cache is the Modal Volume — weights survive container restarts
        self._model = TribeModel.from_pretrained(
            "facebook/tribev2",
            cache_folder="/cache",
        )
        # Pre-load Destrieux atlas (cached in volume after first run)
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
    """Smoke test: modal run modal_tribe.py"""
    scorer = TribeScorer()

    cases = [
        ("WARNING: Your account will be DELETED in 24 hours unless you act NOW!", "manipulative"),
        ("The committee meets quarterly to review audited financial statements.", "neutral"),
    ]
    for text, label in cases:
        result = scorer.score.remote(text)
        print(f"\n[{label}]")
        for k, v in result.items():
            print(f"  {k}: {v}")
