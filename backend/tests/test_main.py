from unittest.mock import patch

from fastapi.testclient import TestClient

from models import AnalyzeResponse
import main


client = TestClient(main.app)

AUTH = {"X-ZDrive-API-Key": "znl_test_key_for_unit_tests"}


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


def test_health_no_auth_required():
    r = client.get("/health")
    assert r.status_code == 200


def test_analyze_returns_contract_shape():
    with patch.object(main, "_score_fast", return_value=_stub_response()) as m:
        r = client.post("/analyze", json={"text": "Only 2 left! Buy now!"}, headers=AUTH)
    assert r.status_code == 200
    body = r.json()
    assert set(body.keys()) == {
        "limbic_score",
        "pfc_score",
        "manipulation_index",
        "dominant_technique",
        "confidence",
        "scorer",
        "roi_detail",
    }
    assert body["dominant_technique"] == "urgency"
    assert body["scorer"] == "llm"
    m.assert_called_once()


def test_analyze_rejects_empty_text():
    r = client.post("/analyze", json={"text": ""}, headers=AUTH)
    assert r.status_code == 422  # pydantic validation


def test_analyze_uses_cache_on_second_call(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "_cache", main.AnalysisCache(disk_path=tmp_path / "c.json"))
    with patch.object(main, "_score_fast", return_value=_stub_response()) as m:
        client.post("/analyze", json={"text": "cache this text"}, headers=AUTH)
        client.post("/analyze", json={"text": "cache this text"}, headers=AUTH)
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


# ── Auth middleware tests ─────────────────────────────────────────────────

def test_analyze_rejects_no_auth():
    r = client.post("/analyze", json={"text": "Should be rejected"})
    assert r.status_code == 401
    assert r.json()["error"] == "Unauthorized"


def test_analyze_rejects_short_key():
    r = client.post("/analyze", json={"text": "test"}, headers={"X-ZDrive-API-Key": "znl_short"})
    assert r.status_code == 401


def test_analyze_rejects_wrong_prefix():
    r = client.post("/analyze", json={"text": "test"}, headers={"X-ZDrive-API-Key": "sk_random_key_1234567890"})
    assert r.status_code == 401


def test_analyze_accepts_valid_znl_key():
    with patch.object(main, "_score_fast", return_value=_stub_response()):
        r = client.post("/analyze", json={"text": "Some valid text here"}, headers=AUTH)
    assert r.status_code == 200


def test_analyze_accepts_internal_service_key(monkeypatch):
    monkeypatch.setattr(main, "INTERNAL_KEY", "znl_svc_internal_test_key_1234")
    with patch.object(main, "_score_fast", return_value=_stub_response()):
        r = client.post(
            "/analyze",
            json={"text": "Some valid text here"},
            headers={"X-ZDrive-API-Key": "znl_svc_internal_test_key_1234"},
        )
    assert r.status_code == 200
