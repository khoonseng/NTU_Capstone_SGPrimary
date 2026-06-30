"""DAG: ML Subscription Rate Training

Manually triggered to train and register the LightGBM subscription rate model.
Logs params, metrics, and model artifact to MLflow, then writes predictions to
BigQuery. Requires the MLflow server (pipeline/mlflow/) to be running.

Trigger via Airflow UI:
    DAGs → ml_subscription_rate_training → Trigger DAG w/ config
    Config: {"train_start_year": 2019, "train_end_year": 2023,
             "eval_start_year": 2024, "eval_end_year": 2025}

Task chain:
    train_and_register → validate_predictions
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.models.param import Param
from airflow.providers.standard.operators.bash import BashOperator


with DAG(
    dag_id="ml_subscription_rate_training",
    description="Train LightGBM subscription rate model, log to MLflow, write predictions to BigQuery",
    start_date=datetime(2026, 1, 1),
    schedule=None,
    catchup=False,
    max_active_runs=1,
    tags=["ml", "lightgbm", "mlflow"],
    params={
        "train_start_year": Param(
            2020,
            type="integer",
            description="First year of training data (e.g. 2019 or 2020)",
        ),
        "train_end_year": Param(
            2023,
            type="integer",
            description="Last year of training data",
        ),
        "eval_start_year": Param(
            2024,
            type="integer",
            description="First year of holdout evaluation",
        ),
        "eval_end_year": Param(
            2025,
            type="integer",
            description="Last year of holdout evaluation",
        ),
    },
) as dag:

    # ── Task 1 ─────────────────────────────────────────────────────────────────
    # Train LightGBM model, log params/metrics/artifact to MLflow, register model,
    # and write current-year predictions to sg_moe_star.mart_ml_predictions.
    # MLflow is reachable by container name via the shared sgprimary-net network.
    train_and_register = BashOperator(
        task_id="train_and_register",
        bash_command=(
            "python /opt/airflow/ml/train.py "
            "--train-start-year {{ params.train_start_year }} "
            "--train-end-year {{ params.train_end_year }} "
            "--eval-start-year {{ params.eval_start_year }} "
            "--eval-end-year {{ params.eval_end_year }} "
            "--tracking-uri http://sgprimary-mlflow:5000"
        ),
        retries=1,
        retry_delay=timedelta(minutes=2),
    )

    # ── Task 2 ─────────────────────────────────────────────────────────────────
    # Confirm predictions were written to BigQuery for the current year.
    # Exits non-zero (fails the task) if no rows are found.
    validate_predictions = BashOperator(
        task_id="validate_predictions",
        bash_command="""
python << 'PYEOF'
import os, sys
from datetime import date
from google.cloud import bigquery

project = os.environ['GCP_PROJECT_ID']
year    = date.today().year

client = bigquery.Client(project=project)
sql    = (
    'SELECT COUNT(*) AS cnt '
    'FROM `' + project + '.sg_moe_star.mart_ml_predictions` '
    'WHERE registration_year = ' + str(year)
)
row = next(client.query(sql).result())
cnt = row['cnt']
print(f'mart_ml_predictions year={year}: {cnt} rows')
if cnt == 0:
    print(f'ERROR: No predictions found for year {year}. Training or BQ write may have failed.')
    sys.exit(1)
print('Validation passed.')
PYEOF
""",
    )

    # ── Dependency chain ───────────────────────────────────────────────────────
    train_and_register >> validate_predictions
