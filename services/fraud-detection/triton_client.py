"""
Triton HTTP client for the fraud-detection service.

Sends an inference request to Triton using the KServe v2 HTTP protocol.

The fraud model exposes two output tensors:
  - ``label``         INT64  [batch, 1]  — predicted class (0 = legit, 1 = fraud)
  - ``probabilities`` FP32   [batch, 2]  — [P(legit), P(fraud)] per row

``infer`` returns the per-row fraud probability (``probabilities[:, 1]``) as a
flat Python list so the caller can apply its own threshold logic.
"""
import logging

import numpy as np
import tritonclient.http as httpclient
from tritonclient.utils import InferenceServerException

logger = logging.getLogger(__name__)

# Names that match the fraud model's tensor spec.
_INPUT_NAME = "float_input"
_OUTPUT_LABEL = "label"
_OUTPUT_PROBS = "probabilities"


class TritonClientError(Exception):
    """Raised when Triton returns an error or is unreachable."""


class TritonClient:
    def __init__(self, url: str, model_name: str) -> None:
        # url is expected without scheme, e.g. "localhost:8000"
        host = url.removeprefix("http://").removeprefix("https://")
        self._client = httpclient.InferenceServerClient(url=host, verbose=False)
        self._model_name = model_name

    def is_ready(self) -> bool:
        """Return True when the model is loaded and ready to accept requests."""
        try:
            return self._client.is_model_ready(self._model_name)
        except InferenceServerException:
            return False

    def infer(self, features: list[list[float]]) -> list[float]:
        """
        Run inference for a batch of feature rows.

        Args:
            features: List of feature rows, e.g. [[f0, f1, ..., f6], ...]
                      Each row must have exactly 7 float features.

        Returns:
            Flat list of fraud probabilities (one per input row), drawn from
            index 1 of the ``probabilities`` output tensor.

        Raises:
            TritonClientError: on any Triton-side or network error.
        """
        try:
            arr = np.array(features, dtype=np.float32)
            infer_input = httpclient.InferInput(_INPUT_NAME, arr.shape, "FP32")
            infer_input.set_data_from_numpy(arr)

            infer_outputs = [
                httpclient.InferRequestedOutput(_OUTPUT_LABEL),
                httpclient.InferRequestedOutput(_OUTPUT_PROBS),
            ]

            result = self._client.infer(
                model_name=self._model_name,
                inputs=[infer_input],
                outputs=infer_outputs,
            )

            # probabilities shape: [batch, 2] — column 1 is P(fraud)
            probs = result.as_numpy(_OUTPUT_PROBS)
            fraud_probs = probs[:, 1]

            labels = result.as_numpy(_OUTPUT_LABEL).flatten().tolist()
            logger.debug("label=%s probabilities=%s", labels, probs.tolist())

            return fraud_probs.flatten().tolist()
        except InferenceServerException as exc:
            raise TritonClientError(str(exc)) from exc
        except Exception as exc:
            raise TritonClientError(f"Unexpected error calling Triton: {exc}") from exc
