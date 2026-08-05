"""
Tests for the fraud-detection FastAPI application.
"""
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient


# Patch the Triton client before importing app so startup doesn't dial out
@pytest.fixture(autouse=True)
def _patch_triton_client():
    with patch("app.TritonClient") as mock_cls:
        mock_instance = MagicMock()
        mock_instance.is_ready.return_value = True
        mock_cls.return_value = mock_instance
        yield mock_instance


@pytest.fixture()
def client(_patch_triton_client):
    from app import app
    with TestClient(app) as c:
        yield c, _patch_triton_client


class TestHealth:
    def test_health_returns_200(self, client):
        c, _ = client
        resp = c.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}

    def test_ready_when_model_ready(self, client):
        c, mock_triton = client
        mock_triton.is_ready.return_value = True
        resp = c.get("/ready")
        assert resp.status_code == 200

    def test_ready_503_when_model_not_ready(self, client):
        c, mock_triton = client
        mock_triton.is_ready.return_value = False
        resp = c.get("/ready")
        assert resp.status_code == 503


class TestScore:
    def test_approve_below_review_threshold(self, client):
        c, mock_triton = client
        mock_triton.infer.return_value = [0.1]
        resp = c.post("/score", json={"inputs": [[0.1, 0.2, 0.3]]})
        assert resp.status_code == 200
        body = resp.json()
        assert body["decision"] == "APPROVE"
        assert body["fraud_probability"] == pytest.approx(0.1)

    def test_review_between_thresholds(self, client):
        c, mock_triton = client
        mock_triton.infer.return_value = [0.55]
        resp = c.post("/score", json={"inputs": [[0.5, 0.5, 0.5]]})
        assert resp.status_code == 200
        assert resp.json()["decision"] == "REVIEW"

    def test_decline_above_decline_threshold(self, client):
        c, mock_triton = client
        mock_triton.infer.return_value = [0.85]
        resp = c.post("/score", json={"inputs": [[0.9, 0.9, 0.9]]})
        assert resp.status_code == 200
        assert resp.json()["decision"] == "DECLINE"

    def test_empty_inputs_rejected(self, client):
        c, _ = client
        resp = c.post("/score", json={"inputs": []})
        assert resp.status_code == 422

    def test_triton_error_returns_502(self, client):
        from triton_client import TritonClientError
        c, mock_triton = client
        mock_triton.infer.side_effect = TritonClientError("timeout")
        resp = c.post("/score", json={"inputs": [[1.0, 2.0]]})
        assert resp.status_code == 502

    def test_request_id_echoed_in_response_header(self, client):
        c, mock_triton = client
        mock_triton.infer.return_value = [0.2]
        resp = c.post(
            "/score",
            json={"inputs": [[0.1]]},
            headers={"X-Request-ID": "test-id-123"},
        )
        assert resp.headers.get("X-Request-ID") == "test-id-123"
