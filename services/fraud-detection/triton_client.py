"""
Triton HTTP client for the fraud-detection service.

Sends an inference request to Triton using the KServe v2 HTTP protocol
and returns the raw output tensor as a flat Python list.
"""
import logging

import numpy as np
import tritonclient.http as httpclient
from tritonclient.utils import InferenceServerException

logger = logging.getLogger(__name__)


class TritonClientError(Exception):
    """Raised when Triton returns an error or is unreachable."""


class TritonClient:
    def __init__(self, url: str, model_name: str) -> None:
        # url is expected without scheme, e.g. "localhost:8000"
        host = url.removeprefix("http://").removeprefix("https://")
        self._client = httpclient.InferenceServerClient(url=host, verbose=False)
        self._model_name = model_name
        self._input_name: str | None = None
        self._output_name: str | None = None

    def _load_tensor_names(self) -> None:
        """Resolve input/output tensor names from Triton model metadata."""
        meta = self._client.get_model_metadata(self._model_name)
        self._input_name = meta["inputs"][0]["name"]
        self._output_name = meta["outputs"][0]["name"]
        logger.info(
            "model=%s input=%s output=%s",
            self._model_name,
            self._input_name,
            self._output_name,
        )

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
            features: List of feature rows, e.g. [[f0, f1, ..., fN], ...]

        Returns:
            Flat list of output scores, one per input row.

        Raises:
            TritonClientError: on any Triton-side or network error.
        """
        try:
            if self._input_name is None:
                self._load_tensor_names()

            arr = np.array(features, dtype=np.float32)
            infer_input = httpclient.InferInput(self._input_name, arr.shape, "FP32")
            infer_input.set_data_from_numpy(arr)

            result = self._client.infer(
                model_name=self._model_name,
                inputs=[infer_input],
            )
            output = result.as_numpy(self._output_name)
            return output.flatten().tolist()
        except InferenceServerException as exc:
            raise TritonClientError(str(exc)) from exc
        except Exception as exc:
            raise TritonClientError(f"Unexpected error calling Triton: {exc}") from exc
