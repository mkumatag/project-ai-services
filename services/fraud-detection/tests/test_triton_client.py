"""
Tests for TritonClient.

The fraud model returns two outputs:
  - ``label``         INT64  [batch, 1]
  - ``probabilities`` FP32   [batch, 2]  — [P(legit), P(fraud)]

TritonClient.infer() must return the fraud probability (column 1) for each row.
"""
import pytest
from unittest.mock import MagicMock, call, patch
import numpy as np


# 7-feature transaction matching the real model's float_input tensor
_TRANSACTION = [[9.5, 3.5, 10.0, 1.0, 0.0, 0.0, 1.0]]


class TestTritonClient:
    @pytest.fixture()
    def mock_http_client(self):
        with patch("triton_client.httpclient.InferenceServerClient") as mock_cls:
            yield mock_cls.return_value

    @pytest.fixture()
    def triton_client(self, mock_http_client):
        from triton_client import TritonClient
        return TritonClient(url="http://localhost:8000", model_name="fraud"), mock_http_client

    def _make_result(self, label: int, prob_legit: float, prob_fraud: float) -> MagicMock:
        """Build a mock Triton result with the two-output contract."""
        mock_result = MagicMock()

        def _as_numpy(name):
            if name == "label":
                return np.array([[label]], dtype=np.int64)
            if name == "probabilities":
                return np.array([[prob_legit, prob_fraud]], dtype=np.float32)
            raise ValueError(f"unexpected output name: {name}")

        mock_result.as_numpy.side_effect = _as_numpy
        return mock_result

    def test_is_ready_true(self, triton_client):
        client, mock_http = triton_client
        mock_http.is_model_ready.return_value = True
        assert client.is_ready() is True

    def test_is_ready_false_on_exception(self, triton_client):
        from tritonclient.utils import InferenceServerException
        client, mock_http = triton_client
        mock_http.is_model_ready.side_effect = InferenceServerException("err")
        assert client.is_ready() is False

    def test_infer_returns_fraud_probability(self, triton_client):
        """infer() must return P(fraud) — probabilities[:, 1]."""
        client, mock_http = triton_client
        mock_http.infer.return_value = self._make_result(
            label=1, prob_legit=-1.19e-7, prob_fraud=1.0
        )

        scores = client.infer(_TRANSACTION)
        assert scores == pytest.approx([1.0], abs=1e-5)

    def test_infer_requests_both_outputs(self, triton_client):
        """The client must explicitly request both label and probabilities."""
        import tritonclient.http as httpclient
        client, mock_http = triton_client
        mock_http.infer.return_value = self._make_result(0, 0.9, 0.1)

        with patch.object(httpclient, "InferRequestedOutput", wraps=httpclient.InferRequestedOutput) as mock_out:
            client.infer(_TRANSACTION)

        names_requested = [c.args[0] for c in mock_out.call_args_list]
        assert "label" in names_requested
        assert "probabilities" in names_requested

    def test_infer_uses_correct_input_tensor_name(self, triton_client):
        """Input tensor must be named float_input (matches model spec)."""
        import tritonclient.http as httpclient
        client, mock_http = triton_client
        mock_http.infer.return_value = self._make_result(0, 0.9, 0.1)

        with patch.object(httpclient, "InferInput", wraps=httpclient.InferInput) as mock_in:
            client.infer(_TRANSACTION)

        assert mock_in.call_args.args[0] == "float_input"

    def test_infer_raises_triton_client_error_on_server_exception(self, triton_client):
        from tritonclient.utils import InferenceServerException
        from triton_client import TritonClientError
        client, mock_http = triton_client
        mock_http.infer.side_effect = InferenceServerException("model not found")

        with pytest.raises(TritonClientError, match="model not found"):
            client.infer(_TRANSACTION)

    def test_infer_raises_triton_client_error_on_unexpected_exception(self, triton_client):
        from triton_client import TritonClientError
        client, mock_http = triton_client
        mock_http.infer.side_effect = RuntimeError("network timeout")

        with pytest.raises(TritonClientError, match="network timeout"):
            client.infer(_TRANSACTION)
