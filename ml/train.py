"""
ml/train.py

LightGBM regression model to predict subscription_rate per school × phase.

Pipeline:
  1. Load historical mart_school_analysis + dim_school from BigQuery
  2. Engineer lag features (year-gap-safe via explicit merge, not shift)
  3. Train on 2020–2023, evaluate on 2024–2025 holdout
  4. Generate predictions for current calendar year
  5. Write predictions to sg_moe_star.mart_ml_predictions (WRITE_TRUNCATE)

MLflow integration is deferred — metrics are printed to terminal only.

Usage:
    python ml/train.py
"""

from __future__ import annotations

import os
from datetime import date
from pathlib import Path

import joblib
import lightgbm as lgb
import pandas as pd
from dotenv import load_dotenv
from google.cloud import bigquery
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

GCP_PROJECT_ID = os.environ["GCP_PROJECT_ID"]
DATASET_STAR   = f"{GCP_PROJECT_ID}.sg_moe_star"

COMPETITIVE_PHASES = ("2B", "2C", "2C(S)")
TRAIN_YEARS        = (2020, 2021, 2022, 2023)
EVAL_YEARS         = (2024, 2025)

CATEGORICAL = ["phase", "zone_code", "nature_code"]
NUMERIC     = [
    "lag1", "lag2", "lag3", "rate_3yr_mean", "lag1_vacancy",
    "year", "sap_ind", "autonomous_ind", "gifted_ind",
]
FEATURES    = CATEGORICAL + NUMERIC
TARGET      = "subscription_rate"

MODEL_DIR     = Path(__file__).resolve().parent / "model"
MODEL_PATH    = MODEL_DIR / "lgbm_subscr_rate.pkl"
MODEL_VERSION = "lgbm_v1"

BQ_SCHEMA = [
    bigquery.SchemaField("school_name",                 "STRING",    "REQUIRED"),
    bigquery.SchemaField("phase",                       "STRING",    "REQUIRED"),
    bigquery.SchemaField("registration_year",           "INTEGER",   "REQUIRED"),
    bigquery.SchemaField("predicted_subscription_rate", "FLOAT64",   "REQUIRED"),
    bigquery.SchemaField("predicted_ballot_chance_pct", "FLOAT64",   "REQUIRED"),
    bigquery.SchemaField("model_version",               "STRING",    "REQUIRED"),
    bigquery.SchemaField("trained_at",                  "TIMESTAMP", "REQUIRED"),
]


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

def split(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    # Rows where the phase was not opened have null subscription_rate — exclude them.
    df = df.dropna(subset=[TARGET])
    train = df[df["registration_year"].isin(TRAIN_YEARS)]
    eval_ = df[df["registration_year"].isin(EVAL_YEARS)]
    return train, eval_


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------

def train(train_df: pd.DataFrame) -> lgb.LGBMRegressor:
    model = lgb.LGBMRegressor(
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
    model.fit(
        train_df[FEATURES],
        train_df[TARGET],
        categorical_feature=CATEGORICAL,
    )
    return model


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------

def evaluate(model: lgb.LGBMRegressor, eval_df: pd.DataFrame) -> None:
    y    = eval_df[TARGET]
    pred = model.predict(eval_df[FEATURES])

    mae  = mean_absolute_error(y, pred)
    rmse = mean_squared_error(y, pred) ** 0.5
    r2   = r2_score(y, pred)

    print(f"\n{'─' * 50}")
    print(f"  Holdout evaluation: {EVAL_YEARS[0]}–{EVAL_YEARS[-1]}  (N={len(y)})")
    print(f"  MAE  : {mae:.4f}")
    print(f"  RMSE : {rmse:.4f}")
    print(f"  R²   : {r2:.4f}")

    print(f"\n  Per-phase MAE:")
    for phase in COMPETITIVE_PHASES:
        mask = eval_df["phase"] == phase
        if not mask.any():
            continue
        p_mae = mean_absolute_error(y[mask], model.predict(eval_df.loc[mask, FEATURES]))
        print(f"    Phase {phase:<6} MAE={p_mae:.4f}  N={int(mask.sum())}")

    print(f"\n  Feature importances (top 10 by split count):")
    imp = (
        pd.Series(model.feature_importances_, index=model.feature_name_)
        .sort_values(ascending=False)
    )
    for feat, score in imp.head(10).items():
        print(f"    {feat:<25} {int(score):>5}")
    print(f"{'─' * 50}\n")


# ---------------------------------------------------------------------------
# Prediction rows for current year
# ---------------------------------------------------------------------------

def build_prediction_rows(df: pd.DataFrame, predict_year: int) -> pd.DataFrame:
    """
    One prediction row per school-phase for `predict_year`.
    Lag features derived from the 3 most recent completed years.
    School-phase combinations with no data in any of the last 3 years are dropped.
    """
    # Latest school-level attributes per school-phase (static — use most recent row)
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

    # Drop school-phases with no history in any of the last 3 years
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

def write_predictions(client: bigquery.Client, pred_df: pd.DataFrame) -> None:
    trained_at = pd.Timestamp.now("UTC")

    out = pred_df[["school_name", "phase", "registration_year",
                   "predicted_subscription_rate", "predicted_ballot_chance_pct"]].copy()
    out["model_version"] = MODEL_VERSION
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
    predict_year = date.today().year   # never hardcoded — follows project design rule

    client = bigquery.Client(project=GCP_PROJECT_ID)

    print("Loading historical data from BigQuery...")
    df = load_historical(client)

    print("Engineering lag features...")
    df = engineer_features(df)

    train_df, eval_df = split(df)
    print(f"  Train: {len(train_df)} rows  ({min(TRAIN_YEARS)}–{max(TRAIN_YEARS)})")
    print(f"  Eval : {len(eval_df)} rows  ({min(EVAL_YEARS)}–{max(EVAL_YEARS)})")

    print("\nTraining LightGBM model...")
    model = train(train_df)

    evaluate(model, eval_df)

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    print(f"Model artifact saved → {MODEL_PATH}")

    print(f"\nBuilding prediction rows for {predict_year}...")
    pred_rows = build_prediction_rows(df, predict_year)
    print(f"  {len(pred_rows)} school-phase combinations")

    raw_preds = model.predict(pred_rows[FEATURES])
    pred_rows["predicted_subscription_rate"] = raw_preds.clip(min=0.0)
    pred_rows["predicted_ballot_chance_pct"] = pred_rows["predicted_subscription_rate"].apply(
        lambda r: 1.0 if r <= 1.0 else min(1.0, 1.0 / r)
    )

    print(f"\nWriting predictions to BigQuery...")
    write_predictions(client, pred_rows)

    print("\nDone.")


if __name__ == "__main__":
    main()
