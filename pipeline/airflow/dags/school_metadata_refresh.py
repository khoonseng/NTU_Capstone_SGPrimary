"""DAG 2: School Metadata Refresh

Manually triggered for an annual refresh of school metadata from data.gov.sg.
Fetches current school records, loads to BigQuery, then runs a full dbt build
to propagate changes through all downstream models.

Trigger via Airflow UI:
    DAGs → school_metadata_refresh → Trigger DAG (no config required)

Task chain:
    fetch_and_load_schools → run_dbt_build → validate_row_count

Note: load_schools_data.py fetches from the data.gov.sg API and writes to
BigQuery in a single atomic call (no separate fetch/load steps). The original
4-step chain is condensed to 3 tasks to avoid modifying the existing script.

A full dbt build is used here (not selective) because school metadata changes
propagate through all models — dim_school, fact_balloting, mart_school_analysis
all reference school attributes. Compare with DAG 1 which uses a selective build
(only models downstream of the balloting data change).
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.providers.standard.operators.bash import BashOperator


with DAG(
    dag_id="school_metadata_refresh",
    description="Refresh school metadata from data.gov.sg, load to BigQuery, run full dbt build",
    start_date=datetime(2026, 1, 1),
    schedule=None,       # Manual trigger — run annually or when school data changes
    catchup=False,
    max_active_runs=1,
    tags=["p1-registration", "batch", "schools-metadata"],
) as dag:

    # ── Task 1 ─────────────────────────────────────────────────────────────────
    # Fetch all school records from data.gov.sg REST API and load to
    # sg_moe.raw_schools in BigQuery. The script handles both steps atomically.
    fetch_and_load_schools = BashOperator(
        task_id="fetch_and_load_schools",
        bash_command="python /opt/airflow/scripts/load_schools_data.py",
        retries=2,
        retry_delay=timedelta(minutes=5),
    )

    # ── Task 2 ─────────────────────────────────────────────────────────────────
    # Full dbt build — all models are rebuilt because school metadata changes
    # flow into dim_school, dim_school_generalinfo, fact_balloting, and
    # mart_school_analysis.
    run_dbt_build = BashOperator(
        task_id="run_dbt_build",
        bash_command=(
            "cd /opt/airflow/sg_primary_dbt && "
            "dbt build --profiles-dir ."
        ),
        retries=1,
        retry_delay=timedelta(minutes=3),
    )

    # ── Task 3 ─────────────────────────────────────────────────────────────────
    # Confirm that rows exist in the raw_schools table after the load.
    # Exits non-zero (fails the task) if no rows are found.
    validate_row_count = BashOperator(
        task_id="validate_row_count",
        bash_command="""
python << 'PYEOF'
import os, sys
from google.cloud import bigquery

project = os.environ['GCP_PROJECT_ID']
dataset = os.environ['BQ_DATASET']

client  = bigquery.Client(project=project)
sql     = (
    'SELECT COUNT(*) AS cnt '
    'FROM `' + project + '.' + dataset + '.raw_schools`'
)
row = next(client.query(sql).result())
cnt = row['cnt']
print(f'raw_schools: {cnt} rows')
if cnt == 0:
    print('ERROR: No rows found in raw_schools. Fetch or load may have failed.')
    sys.exit(1)
print('Validation passed.')
PYEOF
""",
    )

    # ── Dependency chain ───────────────────────────────────────────────────────
    fetch_and_load_schools >> run_dbt_build >> validate_row_count
