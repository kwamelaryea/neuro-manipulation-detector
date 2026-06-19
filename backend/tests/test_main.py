from unittest.mock import patch

from fastapi.testclient import TestClient

from models import AnalyzeResponse
import main


client = TestClient(main.app)


def _stub_response():
    return AnalyzeResponse(
        limbic_score=0.6,
        pfc_score=0.3,
        manipulation_index=5.5,
        dominant_technique="urgency",
        confidence="medium",
    )


def test_health_ok():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_analyze_returns_contract_shape():
    with patch.object(main, "score_text", return_value=_stub_response()) as m:
        r = client.post("/analyze", json={"text": "Only 2 left! Buy now!"})
    assert r.status_code == 200
    body = r.json()
    assert set(body.keys()) == {
        "limbic_score",
        "pfc_score",
        "manipulation_index",
        "dominant_technique",
        "confidence",
    }
    assert body["dominant_technique"] == "urgency"
    m.assert_called_once()


def test_analyze_rejects_empty_text():
    r = client.post("/analyze", json={"text": ""})
    assert r.status_code == 422  # pydantic validation


def test_analyze_uses_cache_on_second_call(tmp_path, monkeypatch):
    # Point cache at a temp file and reset the singleton.
    monkeypatch.setattr(main, "_cache", main.AnalysisCache(disk_path=tmp_path / "c.json"))
    with patch.object(main, "score_text", return_value=_stub_response()) as m:
        client.post("/analyze", json={"text": "cache this text"})
        client.post("/analyze", json={"text": "cache this text"})
    # Scorer called once; second hit served from cache.
    assert m.call_count == 1


def test_cors_header_present():
    r = client.options(
        "/analyze",
        headers={
            "Origin": "chrome-extension://abc",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert r.headers.get("access-control-allow-origin") is not None
