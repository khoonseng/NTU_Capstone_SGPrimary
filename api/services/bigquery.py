"""
services/bigquery.py

Shared BigQuery query execution helper.

All routers and services call run_query() rather than instantiating
their own BigQuery clients. This keeps credential handling in one place
and makes it straightforward to add query logging or caching later.
"""

from google.cloud import bigquery
from api.config import get_bq_client, get_settings


def run_query(sql: str, params: list[bigquery.ScalarQueryParameter] | None = None) -> list[dict]:
    """
    Executes a parameterised BigQuery SQL query and returns results
    as a list of dicts.

    Using parameterised queries (QueryJobConfig with query_parameters)
    rather than f-string interpolation prevents SQL injection and lets
    BigQuery cache query plans more effectively.

    Args:
        sql:    BigQuery SQL string with @param_name placeholders.
        params: List of ScalarQueryParameter objects. Pass None for
                queries with no parameters.

    Returns:
        List of dicts — one dict per result row, keyed by column name.
    """
    client = get_bq_client()

    job_config = bigquery.QueryJobConfig(
        query_parameters=params or []
    )

    query_job = client.query(sql, job_config=job_config)
    results = query_job.result()

    return [dict(row) for row in results]


def get_dataset() -> str:
    """
    Returns the fully qualified BigQuery dataset prefix for the star schema.
    Used to build table references in SQL strings.

    Example return: "test-sg-moe.sg_moe_star"
    """
    settings = get_settings()
    return f"{settings.gcp_project_id}.sg_moe_star"