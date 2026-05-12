"""
config.py

Centralised configuration for the SGPrimary FastAPI application.
Reads environment variables via pydantic-settings.

All BigQuery client initialisation happens here — routers and services
import `get_bq_client()` rather than instantiating their own clients.
This ensures a single client instance is reused across requests.
"""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from google.cloud import bigquery
from pathlib import Path


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    Mirrors the .env file used in scripts/ — no new variables needed.
    """
    gcp_project_id: str
    bq_dataset: str = "sg_moe_star"         # default to the star schema

    # Optional: local dev uses GOOGLE_APPLICATION_CREDENTIALS file path.
    # Cloud Run uses ADC (Application Default Credentials) automatically —
    # this variable will simply be absent in the Cloud Run environment.
    google_application_credentials: str | None = None

    # Points to repo root regardless of where the process is launched from
    _ENV_PATH = Path(__file__).resolve().parent.parent / ".env"

    model_config = SettingsConfigDict(
        env_file=_ENV_PATH,
        env_file_encoding="utf-8",
        case_sensitive=False,               # GCP_PROJECT_ID → gcp_project_id
        extra="ignore",                     # ignore unrelated .env vars
    )


@lru_cache
def get_settings() -> Settings:
    """
    Returns a cached Settings instance.
    lru_cache ensures .env is only read once per process lifetime —
    not on every request.
    """
    return Settings()


def get_bq_client() -> bigquery.Client:
    """
    Initialises and returns a BigQuery client.

    Local dev: authenticates via GOOGLE_APPLICATION_CREDENTIALS in .env.
    Cloud Run: authenticates via ADC — no credential file needed.
    The google-cloud-bigquery library handles both cases automatically.
    """
    settings = get_settings()
    return bigquery.Client(project=settings.gcp_project_id)