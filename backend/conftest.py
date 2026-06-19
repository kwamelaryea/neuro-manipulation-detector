import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))


@pytest.fixture(autouse=True)
def reset_main_cache(monkeypatch):
    """Give every test a clean in-memory cache so disk state doesn't bleed in."""
    try:
        import main
        from cache import AnalysisCache

        monkeypatch.setattr(main, "_cache", AnalysisCache(disk_path=None))
    except ModuleNotFoundError:
        pass  # main.py not yet created — tests for other modules are fine
