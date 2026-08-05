"""
Pydantic settings for the fraud-detection API.
All values are read from environment variables at startup.
"""
import logging

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    triton_http_url: str = Field(
        default="http://localhost:8000",
        description="Base URL of the Triton HTTP endpoint (scheme + host + port).",
    )
    triton_model_name: str = Field(
        default="fraud_model",
        description="Name of the Triton model to call.",
    )
    review_threshold: float = Field(
        default=0.4,
        gt=0.0,
        lt=1.0,
        description="fraud_probability above this value → REVIEW decision.",
    )
    decline_threshold: float = Field(
        default=0.7,
        gt=0.0,
        lt=1.0,
        description="fraud_probability above this value → DECLINE decision.",
    )
    log_level: str = Field(
        default="INFO",
        description="Python logging level (DEBUG, INFO, WARNING, ERROR).",
    )

    @field_validator("decline_threshold")
    @classmethod
    def decline_must_exceed_review(cls, v, info):
        review = info.data.get("review_threshold", 0.0)
        if v <= review:
            raise ValueError(
                f"decline_threshold ({v}) must be greater than review_threshold ({review})"
            )
        return v

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
