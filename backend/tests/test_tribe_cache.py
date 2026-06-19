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
    with patch.object(main, "score_text", return_value=stub) as m:
        client = TestClient(main.app)
        client.post("/analyze", json={"text": "repeated heavy inference text"})
        client.post("/analyze", json={"text": "repeated heavy inference text"})
    assert m.call_count == 1
