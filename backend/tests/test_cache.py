import json

from cache import make_key, AnalysisCache
from models import AnalyzeResponse


def test_make_key_is_sha256_hex():
    key = make_key("Buy now!")
    assert len(key) == 64
    assert all(c in "0123456789abcdef" for c in key)


def test_make_key_is_deterministic():
    assert make_key("same text") == make_key("same text")


def test_make_key_differs_on_different_text():
    assert make_key("a") != make_key("b")


def test_make_key_normalizes_whitespace():
    # Leading/trailing whitespace must not produce distinct keys.
    assert make_key("  hello  ") == make_key("hello")


def _sample() -> AnalyzeResponse:
    return AnalyzeResponse(
        limbic_score=0.7,
        pfc_score=0.3,
        manipulation_index=6.0,
        dominant_technique="urgency",
        confidence="medium",
    )


def test_cache_get_miss_returns_none(tmp_path):
    c = AnalysisCache(disk_path=tmp_path / "store.json")
    assert c.get("any text") is None


def test_cache_set_then_get(tmp_path):
    c = AnalysisCache(disk_path=tmp_path / "store.json")
    c.set("hello", _sample())
    got = c.get("hello")
    assert got is not None
    assert got.dominant_technique == "urgency"


def test_cache_persists_to_disk(tmp_path):
    path = tmp_path / "store.json"
    c1 = AnalysisCache(disk_path=path)
    c1.set("persist me", _sample())

    # New instance loads from disk.
    c2 = AnalysisCache(disk_path=path)
    got = c2.get("persist me")
    assert got is not None
    assert got.limbic_score == 0.7


def test_cache_disk_file_is_valid_json(tmp_path):
    path = tmp_path / "store.json"
    c = AnalysisCache(disk_path=path)
    c.set("x", _sample())
    data = json.loads(path.read_text())
    assert len(data) == 1
