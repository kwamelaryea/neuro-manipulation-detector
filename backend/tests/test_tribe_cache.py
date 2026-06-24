from unittest.mock import patch

import numpy as np

import main
from models import AnalyzeResponse


def test_tribe_path_caches(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    monkeypatch.setattr(main, "_cache", main.AnalysisCache(disk_path=tmp_path / "c.json"))

    stub = AnalyzeResponse(
        limbic_score=0.8, pfc_score=0.2, manipulation_index=7.0,
        dominant_technique="fear", confidence="high",
    )
    auth = {"X-ZDrive-API-Key": "znl_test_key_for_unit_tests"}
    with patch.object(main, "_score_fast", return_value=stub) as m:
        client = TestClient(main.app)
        client.post("/analyze", json={"text": "repeated heavy inference text"}, headers=auth)
        client.post("/analyze", json={"text": "repeated heavy inference text"}, headers=auth)
    assert m.call_count == 1
