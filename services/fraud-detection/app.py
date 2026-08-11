"""
Fraud Detection API

Thin FastAPI application that accepts a transaction feature vector,
calls the Triton inference server, applies threshold logic, and returns
a structured fraud decision.
"""
import logging
import os
import uuid

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.openapi.docs import get_swagger_ui_html
from pydantic import BaseModel, Field

from settings import settings
from triton_client import TritonClient, TritonClientError

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
logging.basicConfig(
    level=log_level,
    format="%(asctime)s %(levelname)s [%(name)s] [req=%(request_id)s] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)

# Inject request_id into every log record via a filter
import contextvars

_request_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar(
    "request_id", default="-"
)


class _RequestIDFilter(logging.Filter):
    def filter(self, record):  # noqa: A003
        record.request_id = _request_id_ctx.get()
        return True


for _h in logging.root.handlers:
    _h.addFilter(_RequestIDFilter())

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Triton client (module-level singleton; initialised at startup)
# ---------------------------------------------------------------------------
_triton: TritonClient | None = None


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------
class ScoreRequest(BaseModel):
    inputs: list[list[float]] = Field(
        ...,
        min_length=1,
        description=(
            "Batch of feature rows. Each row must contain exactly 7 float features: "
            "[distance_from_home, distance_from_last_transaction, ratio_to_median_purchase_price, "
            "repeat_retailer, used_chip, used_pin_number, online_order]."
        ),
        examples=[[[9.5, 3.5, 10.0, 1.0, 0.0, 0.0, 1.0]]],
    )


class ScoreResponse(BaseModel):
    fraud_probability: float = Field(
        ..., description="Fraud probability score for the first input row [0, 1]."
    )
    decision: str = Field(
        ..., description="APPROVE | REVIEW | DECLINE based on configured thresholds."
    )
    model_name: str
    model_version: str = "1"


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
tags_metadata = [
    {"name": "scoring", "description": "Fraud scoring operations"},
    {"name": "monitoring", "description": "Health and readiness checks"},
]

app = FastAPI(
    title="Fraud Detection API",
    description=(
        "Real-time transaction fraud scoring backed by NVIDIA Triton Inference Server.\n\n"
        "Send a feature vector to `/score` and receive a probability score together "
        "with an APPROVE / REVIEW / DECLINE decision."
    ),
    version="1.0.0",
    openapi_tags=tags_metadata,
)


@app.on_event("startup")
def _startup() -> None:
    global _triton
    _triton = TritonClient(
        url=settings.triton_http_url,
        model_name=settings.triton_model_name,
    )
    logger.info(
        "Triton client initialised — url=%s model=%s",
        settings.triton_http_url,
        settings.triton_model_name,
    )


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------
@app.middleware("http")
async def _attach_request_id(request: Request, call_next):
    rid = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    _request_id_ctx.set(rid)
    response = await call_next(request)
    response.headers["X-Request-ID"] = rid
    return response


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/", include_in_schema=False)
def _swagger_root():
    return get_swagger_ui_html(
        openapi_url="/openapi.json",
        title="Fraud Detection API - Swagger UI",
    )


@app.post(
    "/score",
    response_model=ScoreResponse,
    tags=["scoring"],
    summary="Score a transaction",
    description=(
        "Accepts a batch of feature rows and returns a fraud probability score and "
        "decision for the **first row**.\n\n"
        "Decision thresholds (configurable via environment variables):\n\n"
        "| Range | Decision |\n"
        "|---|---|\n"
        "| `< REVIEW_THRESHOLD` | APPROVE |\n"
        "| `>= REVIEW_THRESHOLD` and `< DECLINE_THRESHOLD` | REVIEW |\n"
        "| `>= DECLINE_THRESHOLD` | DECLINE |\n"
    ),
)
async def score(req: ScoreRequest) -> ScoreResponse:
    if _triton is None:
        raise HTTPException(status_code=503, detail="Triton client not initialised")

    try:
        scores = _triton.infer(req.inputs)
    except TritonClientError as exc:
        logger.error("Triton inference error: %s", exc)
        raise HTTPException(status_code=502, detail=f"Inference error: {exc}") from exc

    prob = float(scores[0])

    if prob >= settings.decline_threshold:
        decision = "DECLINE"
    elif prob >= settings.review_threshold:
        decision = "REVIEW"
    else:
        decision = "APPROVE"

    logger.info("score=%.4f decision=%s", prob, decision)

    return ScoreResponse(
        fraud_probability=prob,
        decision=decision,
        model_name=settings.triton_model_name,
    )


@app.get(
    "/health",
    tags=["monitoring"],
    summary="Liveness check",
    description="Returns 200 when the API process is running.",
)
async def health():
    return {"status": "ok"}


@app.get(
    "/ready",
    tags=["monitoring"],
    summary="Readiness check",
    description="Returns 200 when Triton has the model loaded and ready.",
)
async def ready():
    if _triton is None or not _triton.is_ready():
        raise HTTPException(status_code=503, detail="Model not ready")
    return {"status": "ready"}


if __name__ == "__main__":
    port = int(os.getenv("PORT", "9000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
