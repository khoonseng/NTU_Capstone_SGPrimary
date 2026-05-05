"""
ingestion/load_sgschooling_data.py

Step 1: Load data from sgschooling.com into BigQuery for a given year (default: 2025)
Pipeline: Parquet files in GCS → BigQuery

Usage:
    python load_sgschooling_data.py            # scrapes 2025 only
    python load_sgschooling_data.py 2019 2025  # scrapes 2019 to 2025 inclusive (Step 2)
    python load_sgschooling_data.py 2009 2018  # scrapes 2009 to 2018 inclusive (Step 3)
"""

import os
import sys
from dotenv import load_dotenv
from google.cloud import bigquery
from google.cloud.bigquery import RangePartitioning, PartitionRange

load_dotenv()

# ── Config ─────────────────────────────────────────────────────────────────────
GCS_BUCKET   = os.getenv("GCS_BUCKET_NAME")
GCS_PREFIX   = "raw/sgschooling"
BQ_PROJECT   = os.getenv("GCP_PROJECT_ID")
BQ_DATASET   = os.getenv("BQ_DATASET")
BQ_TABLE     = "raw_sgschooling_balloting"

# ── BigQuery schema — mirrors Parquet schema above ─────────────────────────────
BQ_SCHEMA = [
    bigquery.SchemaField("school_name",          "STRING"),
    bigquery.SchemaField("total_vacancy",        "INTEGER"),
    bigquery.SchemaField("phase",                "STRING"),
    bigquery.SchemaField("vacancy",              "INTEGER"),
    bigquery.SchemaField("applied",              "INTEGER"),
    bigquery.SchemaField("taken",                "INTEGER"),
    bigquery.SchemaField("ballot_scenario_code", "STRING"),
    bigquery.SchemaField("ballot_description",   "STRING"),
    bigquery.SchemaField("ballot_applicants",    "INTEGER"),
    bigquery.SchemaField("ballot_vacancies",     "INTEGER"),
    bigquery.SchemaField("ballot_chance_pct",    "FLOAT"),
    bigquery.SchemaField("registration_year",    "INTEGER"),
    bigquery.SchemaField("scraped_at",           "TIMESTAMP"),
]

# ── BigQuery load ──────────────────────────────────────────────────────────────

def load_to_bigquery(gcs_uris: list[str]):
    """
    Load all collected GCS Parquet files into BigQuery in one job.
    Uses WRITE_APPEND so each year's data is added without overwriting others.
    Table is range-partitioned by registration_year.
    """
    client = bigquery.Client(project=BQ_PROJECT)
    table_ref = f"{BQ_PROJECT}.{BQ_DATASET}.{BQ_TABLE}"

    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.PARQUET,
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
        schema=BQ_SCHEMA,
        range_partitioning=RangePartitioning(
            field="registration_year",
            range_=PartitionRange(start=2009, end=2050, interval=1),
        ),
    )

    print(f"\nLoading {len(gcs_uris)} file(s) into {table_ref} ...")
    load_job = client.load_table_from_uri(gcs_uris, table_ref, job_config=job_config)
    load_job.result()  # blocks until complete

    table = client.get_table(table_ref)
    print(f"BigQuery table now has {table.num_rows} total rows.")


# ── Validation query ───────────────────────────────────────────────────────────

def validate_in_bigquery(years: list[int]):
    """Print row counts per year to confirm load was successful."""
    client = bigquery.Client(project=BQ_PROJECT)
    years_str = ", ".join(str(y) for y in years)
    query = f"""
        SELECT registration_year, COUNT(*) AS row_count
        FROM `{BQ_PROJECT}.{BQ_DATASET}.{BQ_TABLE}`
        WHERE registration_year IN ({years_str})
        GROUP BY 1
        ORDER BY 1
    """
    print("\nValidation — row counts per year:")
    for row in client.query(query).result():
        print(f"  {row.registration_year}: {row.row_count} rows")


# ── Main ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Parse year range from CLI args
    # Default: 2025 only
    # Usage: python load_sgschooling.py 2019 2025
    args = sys.argv[1:]
    if len(args) == 0:
        years = [2025]
    elif len(args) == 2:
        start_year, end_year = int(args[0]), int(args[1])
        years = list(range(start_year, end_year + 1))
    else:
        print("Usage: python load_sgschooling_data.py [start_year end_year]")
        sys.exit(1)

    print(f"=== Loading sgschooling.com data into BigQuery for years: {years} ===\n")

    gcs_uris = []
    for year in years:
        blob_name = f"{GCS_PREFIX}/sgschooling_{year}.parquet"
        gcs_uri = f"gs://{GCS_BUCKET}/{blob_name}"
        gcs_uris.append(gcs_uri)

    print(gcs_uris)

    load_to_bigquery(gcs_uris)
    validate_in_bigquery(years)
    print("\n=== Done ===")
