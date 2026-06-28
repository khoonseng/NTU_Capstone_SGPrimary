"""
ml/train.py

LightGBM regression model to predict subscription_rate per school × phase.

Pipeline:
  1. Load historical mart_school_analysis + dim_school from BigQuery
  2. Engineer lag features (year-gap-safe via explicit merge, not shift)
  3. Train on <train_start_year>–<train_end_year>, evaluate on holdout
  4. Log params, metrics, and model artifact to MLflow
  5. Generate predictions for current calendar year
  6. Write predictions to sg_moe_star.mart_ml_predictions (WRITE_TRUNCATE)

Usage:
    python ml/train.py
    python ml/train.py --train-start-year 2019
    python ml/train.py --train-start-year 2019 --train-end-year 2023 \
                       --eval-start-year 2024 --eval-end-year 2025 \
                       --tracking-uri http://localhost:5000
"""

from __future__ import annotations

import argparse
import os
from datetime import date
from pathlib import Path

import joblib
import lightgbm as lgb
import mlflow
import mlflow.lightgbm
import pandas as pd
from mlflow.models import infer_signature
from dotenv import load_dotenv
from google.cloud import bigquery
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

GCP_PROJECT_ID = os.environ["GCP_PROJECT_ID"]
DATASET_STAR   = f"{GCP_PROJECT_ID}.sg_moe_star"

COMPETITIVE_PHASES = ("2B", "2C", "2C(S)")

CATEGORICAL = ["phase", "zone_code", "nature_code"]
NUMERIC     = [
    "lag1", "lag2", "lag3", "rate_3yr_mean", "lag1_vacancy",
    "year", "sap_ind", "autonomous_ind", "gifted_ind",
]
FEATURES = CATEGORICAL + NUMERIC
TARGET   = "subscription_rate"

MODEL_DIR = Path(__file__).resolve().parent / "model"

LGBM_PARAMS: dict = dict(
    n_estimators=300,
    learning_rate=0.05,
    max_depth=5,
    num_leaves=31,
    min_child_samples=5,    # small dataset — keep leaf size small to avoid underfitting
    subsample=0.8,
    colsample_bytree=0.8,
    random_state=42,
    verbose=-1,
)

BQ_SCHEMA = [
    bigquery.SchemaField("school_name",                 "STRING",    "REQUIRED"),
    bigquery.SchemaField("phase",                       "STRING",    "REQUIRED"),
    bigquery.SchemaField("registration_year",           "INTEGER",   "REQUIRED"),
    bigquery.SchemaField("predicted_subscription_rate", "FLOAT64",   "REQUIRED"),
    bigquery.SchemaField("predicted_ballot_chance_pct", "FLOAT64",   "REQUIRED"),
    bigquery.SchemaField("model_version",               "STRING",    "REQUIRED"),
    bigquery.SchemaField("trained_at",                  "TIMESTAMP", "REQUIRED"),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train LightGBM subscription rate model.")
    parser.add_argument(
        "--train-start-year", type=int, default=2020,
        help="First year of training data (default: 2020)",
    )
    parser.add_argument(
        "--train-end-year", type=int, default=2023,
        help="Last year of training data (default: 2023)",
    )
    parser.add_argument(
        "--eval-start-year", type=int, default=2024,
        help="First year of holdout evaluation (default: 2024)",
    )
    parser.add_argument(
        "--eval-end-year", type=int, default=2025,
        help="Last year of holdout evaluation (default: 2025)",
    )
    parser.add_argument(
        "--tracking-uri", default="http://localhost:5000",
        help="MLflow tracking server URI (default: http://localhost:5000)",
    )
    parser.add_argument(
        "--experiment-name", default="sgprimary_subscription_rate",
        help="MLflow experiment name",
    )
    parser.add_argument(
        "--run-name", default=None,
        help="MLflow run name (default: lgbm_<train_start>_<train_end>)",
    )
    parser.add_argument(
        "--model-name", default="sgprimary_subscription_rate",
        help="MLflow registered model name (default: sgprimary_subscription_rate)",
    )
    parser.add_argument(
        "--model-alias", default="champion",
        help="MLflow registered model alias (default: champion)",
    )
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_historical(client: bigquery.Client) -> pd.DataFrame:
    """Load all completed-year data for competitive phases from BigQuery."""
    sql = f"""
        SELECT
            m.school_name_clean   AS school_name,
            m.phase_normalised    AS phase,
            m.registration_year,
            m.subscription_rate,
            m.vacancy,
            d.zone_code,
            d.nature_code,
            d.sap_ind,
            d.autonomous_ind,
            d.gifted_ind
        FROM `{DATASET_STAR}.mart_school_analysis` m
        JOIN `{DATASET_STAR}.dim_school` d USING (school_key)
        WHERE m.phase_normalised IN ('2B', '2C', '2C(S)')
          AND m.is_current_year = FALSE
        ORDER BY m.school_name_clean, m.phase_normalised, m.registration_year
    """
    df = client.query(sql).result().to_dataframe()
    print(f"  {len(df):,} rows  |  {df['school_name'].nunique()} schools  |  "
          f"years {int(df['registration_year'].min())}–{int(df['registration_year'].max())}")
    return df


# ---------------------------------------------------------------------------
# Feature engineering
# Uses explicit year-offset merge instead of groupby.shift() so that year
# gaps (phases not opened in a given year) correctly produce NaN lags rather
# than pairing non-adjacent years.
# ---------------------------------------------------------------------------

def _merge_lag(
    df: pd.DataFrame,
    src: pd.DataFrame,
    lag: int,
    src_col: str,
    alias: str,
) -> pd.DataFrame:
    """Left-join prior-year `src_col` onto `df` as `alias`."""
    shifted = (
        src[["school_name", "phase", "registration_year", src_col]]
        .assign(registration_year=lambda x: x["registration_year"] + lag)
        .rename(columns={src_col: alias})
    )
    return df.merge(shifted, on=["school_name", "phase", "registration_year"], how="left")


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for lag in (1, 2, 3):
        df = _merge_lag(df, df, lag, "subscription_rate", f"lag{lag}")
    df = _merge_lag(df, df, 1, "vacancy", "lag1_vacancy")
    df["rate_3yr_mean"] = df[["lag1", "lag2", "lag3"]].mean(axis=1)
    df["year"] = df["registration_year"]
    for col in ("sap_ind", "autonomous_ind", "gifted_ind"):
        df[col] = df[col].astype(float)
    for col in CATEGORICAL:
        df[col] = df[col].astype("category")
    return df


# ---------------------------------------------------------------------------
# Train / eval split
# ---------------------------------------------------------------------------

def split(
    df: pd.DataFrame,
    train_years: tuple[int, ...],
    eval_years: tuple[int, ...],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    # Rows where the phase was not opened have null subscription_rate — exclude them.
    df = df.dropna(subset=[TARGET])
    train = df[df["registration_year"].isin(train_years)]
    eval_ = df[df["registration_year"].isin(eval_years)]
    return train, eval_


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------

def train(train_df: pd.DataFrame) -> lgb.LGBMRegressor:
    model = lgb.LGBMRegressor(**LGBM_PARAMS)
    model.fit(
        train_df[FEATURES],
        train_df[TARGET],
        categorical_feature=CATEGORICAL,
    )
    return model


# ---------------------------------------------------------------------------
# Evaluation — returns metrics dict and importances Series for MLflow logging
# ---------------------------------------------------------------------------

def evaluate(
    model: lgb.LGBMRegressor,
    eval_df: pd.DataFrame,
    eval_years: tuple[int, ...],
) -> tuple[dict[str, float], pd.Series]:
    y    = eval_df[TARGET]
    pred = model.predict(eval_df[FEATURES])

    mae  = mean_absolute_error(y, pred)
    rmse = mean_squared_error(y, pred) ** 0.5
    r2   = r2_score(y, pred)

    metrics: dict[str, float] = {"mae": mae, "rmse": rmse, "r2": r2}

    print(f"\n{'─' * 50}")
    print(f"  Holdout evaluation: {min(eval_years)}–{max(eval_years)}  (N={len(y)})")
    print(f"  MAE  : {mae:.4f}")
    print(f"  RMSE : {rmse:.4f}")
    print(f"  R²   : {r2:.4f}")

    print(f"\n  Per-phase MAE:")
    for phase in COMPETITIVE_PHASES:
        mask = eval_df["phase"] == phase
        if not mask.any():
            continue
        p_mae = mean_absolute_error(y[mask], model.predict(eval_df.loc[mask, FEATURES]))
        # MLflow metric names cannot contain parentheses — 2C(S) → 2CS
        key = f"mae_phase_{phase.replace('(', '').replace(')', '')}"
        metrics[key] = p_mae
        print(f"    Phase {phase:<6} MAE={p_mae:.4f}  N={int(mask.sum())}")

    print(f"\n  Feature importances (top 10 by split count):")
    imp = (
        pd.Series(model.feature_importances_, index=model.feature_name_)
        .sort_values(ascending=False)
    )
    for feat, score in imp.head(10).items():
        print(f"    {feat:<25} {int(score):>5}")
    print(f"{'─' * 50}\n")

    return metrics, imp


# ---------------------------------------------------------------------------
# Prediction rows for current year
# ---------------------------------------------------------------------------

def build_prediction_rows(df: pd.DataFrame, predict_year: int) -> pd.DataFrame:
    """
    One prediction row per school-phase for `predict_year`.
    Lag features derived from the 3 most recent completed years.
    School-phase combinations with no data in any of the last 3 years are dropped.
    """
    attrs = (
        df.sort_values("registration_year")
        .groupby(["school_name", "phase"])[
            ["zone_code", "nature_code", "sap_ind", "autonomous_ind", "gifted_ind"]
        ]
        .last()
        .reset_index()
    )
    attrs["registration_year"] = predict_year
    attrs["year"] = predict_year

    rates = df[["school_name", "phase", "registration_year", "subscription_rate", "vacancy"]]
    for lag in (1, 2, 3):
        attrs = _merge_lag(attrs, rates, lag, "subscription_rate", f"lag{lag}")
    attrs = _merge_lag(attrs, rates, 1, "vacancy", "lag1_vacancy")
    attrs["rate_3yr_mean"] = attrs[["lag1", "lag2", "lag3"]].mean(axis=1)

    n_before = len(attrs)
    attrs = attrs.dropna(subset=["lag1", "lag2", "lag3"], how="all")
    n_dropped = n_before - len(attrs)
    if n_dropped:
        print(f"  Dropped {n_dropped} school-phase rows with no history in last 3 years")

    for col in ("sap_ind", "autonomous_ind", "gifted_ind"):
        attrs[col] = attrs[col].astype(float)
    for col in CATEGORICAL:
        attrs[col] = attrs[col].astype("category")

    return attrs


# ---------------------------------------------------------------------------
# Write predictions to BigQuery
# ---------------------------------------------------------------------------

def write_predictions(
    client: bigquery.Client,
    pred_df: pd.DataFrame,
    model_version: str,
) -> None:
    trained_at = pd.Timestamp.now("UTC")

    out = pred_df[["school_name", "phase", "registration_year",
                   "predicted_subscription_rate", "predicted_ballot_chance_pct"]].copy()
    out["model_version"] = model_version
    out["trained_at"]    = trained_at
    out["phase"]         = out["phase"].astype(str)

    table_id = f"{DATASET_STAR}.mart_ml_predictions"
    job = client.load_table_from_dataframe(
        out,
        table_id,
        job_config=bigquery.LoadJobConfig(
            schema=BQ_SCHEMA,
            write_disposition="WRITE_TRUNCATE",
        ),
    )
    job.result()
    print(f"Wrote {len(out)} predictions → {table_id}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    args = parse_args()
    predict_year = date.today().year   # never hardcoded — follows project design rule

    train_years   = tuple(range(args.train_start_year, args.train_end_year + 1))
    eval_years    = tuple(range(args.eval_start_year,  args.eval_end_year  + 1))
    model_version = f"lgbm_v1_{args.train_start_year}_{args.train_end_year}"
    model_path    = MODEL_DIR / f"lgbm_subscr_rate_{args.train_start_year}_{args.train_end_year}.pkl"
    run_name      = args.run_name or f"lgbm_{args.train_start_year}_{args.train_end_year}"

    client = bigquery.Client(project=GCP_PROJECT_ID)

    print("Loading historical data from BigQuery...")
    df = load_historical(client)

    print("Engineering lag features...")
    df = engineer_features(df)

    train_df, eval_df = split(df, train_years, eval_years)
    print(f"  Train: {len(train_df)} rows  ({min(train_years)}–{max(train_years)})")
    print(f"  Eval : {len(eval_df)} rows  ({min(eval_years)}–{max(eval_years)})")

    print("\nTraining LightGBM model...")
    model = train(train_df)

    metrics, imp = evaluate(model, eval_df, eval_years)

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, model_path)
    print(f"Model artifact saved → {model_path}")

    # MLflow — log params, metrics, feature importances, and model artifact
    mlflow.set_tracking_uri(args.tracking_uri)
    mlflow.set_experiment(args.experiment_name)

    # Signature only — no input_example to avoid LightGBM categorical dtype mismatch
    # during MLflow's internal validation step
    sample_input = train_df[FEATURES].head(5).copy()
    for col in CATEGORICAL:
        sample_input[col] = sample_input[col].astype(str)
    signature = infer_signature(sample_input, model.predict(train_df[FEATURES].head(5)))

    with mlflow.start_run(run_name=run_name):
        mlflow.log_params({
            "train_start_year": args.train_start_year,
            "train_end_year":   args.train_end_year,
            "eval_start_year":  args.eval_start_year,
            "eval_end_year":    args.eval_end_year,
            "train_size":       len(train_df),
            "eval_size":        len(eval_df),
            "features":         ",".join(FEATURES),
            "target":           TARGET,
            **{k: v for k, v in LGBM_PARAMS.items() if k != "verbose"},
        })

        mlflow.log_metrics(metrics)
        mlflow.log_metrics({f"feat_imp_{feat}": int(score) for feat, score in imp.items()})

        model_info = mlflow.lightgbm.log_model(
            model,
            artifact_path=model_version,
            signature=signature,
        )

        registered = mlflow.register_model(model_info.model_uri, args.model_name)
        mlflow.tracking.MlflowClient().set_registered_model_alias(
            args.model_name, args.model_alias, registered.version
        )

        mlflow.set_tags({
            "model_type":              "lightgbm",
            "predict_year":            str(predict_year),
            "model_version":           model_version,
            "registered_model_name":   args.model_name,
            "registered_model_version": str(registered.version),
            "registered_model_alias":  args.model_alias,
        })

        print(f"Registered: {args.model_name} v{registered.version} @{args.model_alias}")
        print(f"MLflow run logged → {args.tracking_uri}  run_id={mlflow.active_run().info.run_id}")

    print(f"\nBuilding prediction rows for {predict_year}...")
    pred_rows = build_prediction_rows(df, predict_year)
    print(f"  {len(pred_rows)} school-phase combinations")

    raw_preds = model.predict(pred_rows[FEATURES])
    pred_rows["predicted_subscription_rate"] = raw_preds.clip(min=0.0)
    pred_rows["predicted_ballot_chance_pct"] = pred_rows["predicted_subscription_rate"].apply(
        lambda r: 1.0 if r <= 1.0 else min(1.0, 1.0 / r)
    )

    print(f"\nWriting predictions to BigQuery...")
    write_predictions(client, pred_rows, model_version)

    print("\nDone.")


if __name__ == "__main__":
    main()
