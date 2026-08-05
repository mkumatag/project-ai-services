"""
Tests for TritonClient.
"""
import pytest
from unittest.mock import MagicMock, patch
import numpy as np


class TestTritonClient:
    @pytest.fixture()
    def mock_http_client(self):
        with patch("triton_client.httpclient.InferenceServerClient") as mock_cls:
            yield mock_cls.return_value

    @pytest.fixture()
    def triton_client(self, mock_http_client):
        from triton_client import TritonClient
        return TritonClient(url="http://localhost:8000", model_name="fraud_model"), mock_http_client

    def test_is_ready_true(self, triton_client):
        client, mock_http = triton_client
        mock_http.is_model_ready.return_value = True
        assert client.is_ready() is True

    def test_is_ready_false_on_exception(self, triton_client):
        from tritonclient.utils import InferenceServerException
        client, mock_http = triton_client
        mock_http.is_model_ready.side_effect = InferenceServerException("err")
        assert client.is_ready() is False

    def test_infer_returns_scores(self, triton_client):
        client, mock_http = triton_client
        mock_result = MagicMock()
        mock_result.as_numpy.return_value = np.array([[0.75]])
        mock_http.infer.return_value = mock_result

        scores = client.infer([[1.0, 2.0, 3.0]])
        assert scores == pytest.approx([0.75])

    def test_infer_raises_triton_client_error_on_server_exception(self, triton_client):
        from tritonclient.utils import InferenceServerException
        from triton_client import TritonClientError
        client, mock_http = triton_client
        mock_http.infer.side_effect = InferenceServerException("model not found")

        with pytest.raises(TritonClientError, match="model not found"):
            client.infer([[1.0, 2.0]])

    def test_infer_raises_triton_client_error_on_unexpected_exception(self, triton_client):
        from triton_client import TritonClientError
        client, mock_http = triton_client
        mock_http.infer.side_effect = RuntimeError("network timeout")

        with pytest.raises(TritonClientError, match="network timeout"):
            client.infer([[1.0]])
