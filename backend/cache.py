"""SHA256-keyed cache for analysis results.

Phase 2 reuses this verbatim to avoid re-running expensive TRIBE v2 inference.
"""
import hashlib
import json
from pathlib import Path
from typing import Optional, Union

from models import AnalyzeResponse


def make_key(text: str) -> str:
    """Stable SHA256 hex key for a piece of text (whitespace-normalized)."""
    normalized = text.strip()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


class AnalysisCache:
    """SHA256-keyed cache. In-memory dict backed by a JSON file on disk."""

    def __init__(self, disk_path: Union[str, Path] = "cache_store.json"):
        self.disk_path = Path(disk_path)
        self._store: dict[str, dict] = {}
        self._load()

    def _load(self) -> None:
        if self.disk_path.exists():
            try:
                self._store = json.loads(self.disk_path.read_text())
            except (json.JSONDecodeError, OSError):
                self._store = {}

    def _flush(self) -> None:
        self.disk_path.write_text(json.dumps(self._store))

    def get(self, text: str) -> Optional[AnalyzeResponse]:
        key = make_key(text)
        raw = self._store.get(key)
        if raw is None:
            return None
        return AnalyzeResponse(**raw)

    def set(self, text: str, response: AnalyzeResponse) -> None:
        key = make_key(text)
        self._store[key] = response.model_dump()
        self._flush()
