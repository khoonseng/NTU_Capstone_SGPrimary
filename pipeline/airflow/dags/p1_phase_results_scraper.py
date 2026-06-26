"""DAG 1: P1 Phase Results Scraper

Manually triggered after each P1 registration phase result is published on
sgschooling.com. Scrapes the results, loads to BigQuery, runs a selective
dbt build, then validates the row count.

Trigger via Airflow UI:
    DAGs → p1_phase_results_scraper → Trigger DAG w/ config
    Config: {"year": 2026, "phase": "2C"}

Phase result dates (2026):
    Phase 1      — 8 July
    Phase 2A     — 17 July
    Phase 2B     — 27 July
    Phase 2C     — 11 August
    Phase 2C(S)  — 27 August

Task chain:
    scrape_sgschooling → load_to_bigquery → run_dbt_build → validate_row_count

Scripts called via BashOperator — not modified from their original form.
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.models.param import Param
from airflow.providers.standard.operators.bash import BashOperator


with DAG(
    dag_id="p1_phase_results_scraper",
    description="Scrape P1 phase results from sgschooling.com, load to BigQuery, run dbt",
    start_date=datetime(2026, 1, 1),
    schedule=None,       # Manual trigger only — run on each phase result date
    catchup=False,
    max_active_runs=1,
    tags=["p1-registration", "batch", "sgschooling"],
    params={
        "year": Param(
            2026,
            type="integer",
            description="Registration year to scrape (e.g. 2026)",
        ),
        "phase": Param(
            "2C",
            type="string",
            description="Phase result just published — used for audit trail and validation",
            enum=["1", "2A", "2B", "2C", "2C(S)"],
        ),
    },
) as dag:

    # ── Task 1 ─────────────────────────────────────────────────────────────────
    # Scrape sgschooling.com for the given year and upload Parquet to GCS.
    # Calls the existing script unchanged via BashOperator.
    scrape_sgschooling = BashOperator(
        task_id="scrape_sgschooling",
        bash_command=(
            "python /opt/airflow/scripts/scrape_sgschooling.py "
            "{{ params.year }} {{ params.year }}"
        ),
        retries=2,
        retry_delay=timedelta(minutes=5),
    )

    # ── Task 2 ─────────────────────────────────────────────────────────────────
    # Load the GCS Parquet file into BigQuery raw table.
    load_to_bigquery = BashOperator(
        task_id="load_to_bigquery",
        bash_command=(
            "python /opt/airflow/scripts/load_sgschooling_data.py "
            "{{ params.year }} {{ params.year }}"
        ),
        retries=1,
        retry_delay=timedelta(minutes=2),
    )

    # ── Task 3 ─────────────────────────────────────────────────────────────────
    # Selective dbt build — rebuilds only models downstream of the new data.
    # +stg_sgschooling_balloting+ runs: stg → fact_balloting → mart_school_analysis.
    # dim_school and other branches are untouched (school metadata did not change).
    run_dbt_build = BashOperator(
        task_id="run_dbt_build",
        bash_command=(
            "cd /opt/airflow/sg_primary_dbt && "
            "dbt build --select +stg_sgschooling_balloting+ --profiles-dir ."
        ),
        retries=1,
        retry_delay=timedelta(minutes=3),
    )

    # ── Task 4 ─────────────────────────────────────────────────────────────────
    # Confirm that rows for the scraped year exist in the raw table.
    # Exits non-zero (fails the task) if no rows are found.
    validate_row_count = BashOperator(
        task_id="validate_row_count",
        bash_command="""
python << 'PYEOF'
import os, sys
from google.cloud import bigquery

project = os.environ['GCP_PROJECT_ID']
dataset = os.environ['BQ_DATASET']
year    = {{ params.year }}
phase   = '{{ params.phase }}'

client  = bigquery.Client(project=project)
sql     = (
    'SELECT COUNT(*) AS cnt '
    'FROM `' + project + '.' + dataset + '.raw_sgschooling_balloting` '
    'WHERE year = ' + str(year)
)
row = next(client.query(sql).result())
cnt = row['cnt']
print(f'raw_sgschooling_balloting year={year} phase={phase}: {cnt} rows')
if cnt == 0:
    print(f'ERROR: No rows found for year {year}. Scrape or load may have failed.')
    sys.exit(1)
print('Validation passed.')
PYEOF
""",
    )

    # ── Dependency chain ───────────────────────────────────────────────────────
    scrape_sgschooling >> load_to_bigquery >> run_dbt_build >> validate_row_count
