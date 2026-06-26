"""Fetch historical vacancy figures from mart_school_analysis to seed the producer.

Queries the most recent year's vacancy and applicant counts per active school × phase.
The producer uses these as the baseline to generate realistic drift across 6 snapshots.

Usage (standalone verification):
    python seed_data.py

Returns a list of dicts, one per school × phase:
    {school_name, phase, vacancy_at_open, final_applied_count, ballot_risk_level}
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from google.cloud import bigquery

# .env is at the project root — 4 levels up from pipeline/streaming/producer/
load_dotenv(Path(__file__).resolve().parents[4] / ".env")

GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "test-sg-moe")
_BQ_DATASET    = os.getenv("BQ_DATASET", "sg_moe_star")
BQ_STAR_DATASET = (
    _BQ_DATASET if _BQ_DATASET.endswith("_star") else f"{_BQ_DATASET}_star"
)

MART_TABLE = f"{GCP_PROJECT_ID}.{BQ_STAR_DATASET}.mart_school_analysis"

PHASES_TO_SIMULATE = ("2B", "2C", "2C(S)")


def fetch_seed_data() -> list[dict]:
    """Return most recent year's vacancy + applied figures per active school × phase.

    Filters to active schools with full figures and positive vacancy only.
    Uses a dynamic MAX(registration_year) subquery — year is never hardcoded.
    """
    client = bigquery.Client(project=GCP_PROJECT_ID)

    query = f"""
        SELECT
            school_name_clean   AS school_name,
            phase_normalised    AS phase,
            vacancy             AS vacancy_at_open,
            applied             AS final_applied_count,
            ballot_risk_level
        FROM `{MART_TABLE}`
        WHERE registration_year = (
            SELECT MAX(registration_year)
            FROM `{MART_TABLE}`
        )
          AND phase_normalised IN UNNEST(@phases)
          AND is_active = TRUE
          AND has_full_figures = TRUE
          AND vacancy > 0
        ORDER BY school_name_clean, phase_normalised
    """

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ArrayQueryParameter("phases", "STRING", list(PHASES_TO_SIMULATE)),
        ]
    )

    rows = client.query(query, job_config=job_config).result()
    records = [dict(row) for row in rows]
    print(f"Fetched {len(records)} seed records from BigQuery "
          f"({len(set(r['school_name'] for r in records))} schools × "
          f"{len(PHASES_TO_SIMULATE)} phases).")
    return records


if __name__ == "__main__":
    records = fetch_seed_data()
    if records:
        print("\nSample (first 3 records):")
        for r in records[:3]:
            print(r)
