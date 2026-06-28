"""
config.py

Centralised configuration for the SGPrimary FastAPI application.
Reads environment variables via pydantic-settings.

All BigQuery client initialisation happens here — routers and services
import `get_bq_client()` rather than instantiating their own clients.
This ensures a single client instance is reused across requests.
"""

import time
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
    groq_api_key: str | None = None
    advisor_primary_model: str = "llama-3.3-70b-versatile"
    advisor_fallback_models: str = (
        "meta-llama/llama-4-scout-17b-16e-instruct,"
        "llama-3.1-8b-instant,"
        "qwen/qwen3-32b,"
        "openai/gpt-oss-20b,"
        "openai/gpt-oss-120b"
    )
    advisor_show_model_used: bool = False

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

# Module-level settings instance for direct import
settings = get_settings()


# ---------------------------------------------------------------------------
# Feature flags — read from sg_moe_seeds.app_config with a 60-second TTL cache.
# BigQuery infers the config_value column as BOOL from the dbt seed CSV.
# Toggle via BigQuery console:
#   UPDATE `<project>.sg_moe_seeds.app_config`
#   SET config_value = true
#   WHERE config_key = 'show_interim_data'
# ---------------------------------------------------------------------------

_config_cache: dict[str, bool] = {}
_config_cache_expires_at: float = 0.0
_CONFIG_TTL = 60.0  # seconds


def get_app_config_flag(key: str, default: bool = False) -> bool:
    """
    Returns the value of a feature flag from sg_moe_seeds.app_config.

    All flags are loaded in a single BQ query on cache miss so that multiple
    flag reads within one request only cost one round trip. The full table is
    cached for 60 seconds — subsequent calls within that window are local dict
    lookups with no BQ overhead.

    Returns `default` if the key does not exist in the table.
    """
    global _config_cache_expires_at
    now = time.monotonic()
    if now < _config_cache_expires_at:
        return _config_cache.get(key, default)

    client = get_bq_client()
    sql = f"""
        SELECT config_key, config_value
        FROM `{settings.gcp_project_id}.sg_moe_seeds.app_config`
    """
    rows = list(client.query(sql).result())
    _config_cache.clear()
    for row in rows:
        _config_cache[row["config_key"]] = bool(row["config_value"])
    _config_cache_expires_at = now + _CONFIG_TTL
    return _config_cache.get(key, default)