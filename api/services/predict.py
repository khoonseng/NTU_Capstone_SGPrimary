"""
services/predict.py

Business logic for the /predict endpoint.

Queries mart_school_analysis for the requested school and phase.
Returns structured risk assessment with templated risk_explanation.

No is_active filter applied — /predict surfaces historical data for
all schools including inactive ones (merged, relocated) since the
historical data remains valid and merger/relocation context is
useful to parents.

Query strategy:
  Fetches last 3 completed years (registration_year < current_year)
  ordered by registration_year DESC. Most recent row drives prediction.
  No current year sentinel — prediction is based on completed data only.
"""

from datetime import date
from google.cloud import bigquery
from api.services.bigquery import run_query, get_dataset


def _get_current_year() -> int:
    """
    Returns the current calendar year computed at call time.
    Never cached — always accurate across calendar year boundaries.
    """
    return date.today().year


def _build_risk_explanation(
    ballot_risk_level: str | None,
    ballot_occurrences_last_3yr: int | None,
    subscription_rate_3yr_avg: float | None,
    subscription_rate_yoy_change: float | None,
) -> str:
    """
    Generates a human-readable risk explanation from pre-computed
    trend features. Templated server-side — LLM-generated explanations
    are deferred to Week 4 RAG layer.

    Covers four scenarios based on ballot_risk_level and trend direction:
      HIGH + increasing demand
      HIGH + stabilising demand
      MEDIUM
      LOW
    """
    if ballot_risk_level == "HIGH":
        if subscription_rate_yoy_change is not None and subscription_rate_yoy_change > 0:
            return (
                f"Balloted in all 3 of the last 3 years with an average subscription "
                f"rate of {subscription_rate_3yr_avg:.2f}x. "
                f"Demand is increasing year-on-year — competition is intensifying."
            )
        else:
            return (
                f"Balloted in all 3 of the last 3 years with an average subscription "
                f"rate of {subscription_rate_3yr_avg:.2f}x. "
                f"Demand appears to be stabilising but competition remains high."
            )

    elif ballot_risk_level == "MEDIUM":
        return (
            f"Balloted in {ballot_occurrences_last_3yr} of the last 3 years with an "
            f"average subscription rate of {subscription_rate_3yr_avg:.2f}x. "
            f"Monitor closely — this school has shown recent balloting activity."
        )

    else:
        rate_str = (
            f"{subscription_rate_3yr_avg:.2f}x"
            if subscription_rate_3yr_avg is not None
            else "unavailable"
        )
        return (
            f"No balloting in the last 3 years. "
            f"Average subscription rate of {rate_str}. "
            f"Ballot risk is currently low based on recent trends."
        )


def get_prediction(school_name: str, phase: str) -> dict | None:
    """
    Fetches prediction data for the requested school and phase.

    Returns None if no rows are found — caller handles HTTP 404.

    Args:
        school_name: canonical school name, case-insensitive matched
        phase:       normalised phase code e.g. "2C"

    Returns:
        Dict ready for PredictResponse instantiation, or None.
    """
    current_year = _get_current_year()
    dataset = get_dataset()

    params = [
        bigquery.ScalarQueryParameter("school_name", "STRING", school_name.upper().strip()),
        bigquery.ScalarQueryParameter("phase", "STRING", phase),
    ]

    sql = f"""
        SELECT
            m.school_name_clean,
            m.phase_normalised,
            m.school_status,
            m.is_active,
            m.school_status_description,
            m.registration_year,
            m.vacancy,
            m.applied,
            m.taken,
            m.subscription_rate,
            m.ballot_scenario_code,
            m.ballot_chance_pct,
            m.ballot_risk_level,
            m.ballot_occurrences_last_3yr,
            m.ballot_occurrences_last_5yr,
            m.subscription_rate_3yr_avg,
            m.subscription_rate_5yr_avg,
            m.subscription_rate_yoy_change,
            m.vacancy_3yr_avg,
            m.vacancy_yoy_change,
            ROW_NUMBER() OVER (
                PARTITION BY m.school_name_clean, m.phase_normalised
                ORDER BY m.registration_year DESC
            ) AS row_rank
        FROM `{dataset}.mart_school_analysis` m
        WHERE UPPER(TRIM(m.school_name_clean)) = @school_name
          AND m.phase_normalised = @phase
          AND m.registration_year < {current_year}
        ORDER BY m.registration_year DESC
    """

    rows = run_query(sql, params)

    if not rows:
        return None

    # Most recent completed year drives the prediction
    latest = rows[0]

    # Last 3 completed years for history block
    history_rows = rows[:3]

    risk_explanation = _build_risk_explanation(
        ballot_risk_level=latest.get("ballot_risk_level"),
        ballot_occurrences_last_3yr=latest.get("ballot_occurrences_last_3yr"),
        subscription_rate_3yr_avg=latest.get("subscription_rate_3yr_avg"),
        subscription_rate_yoy_change=latest.get("subscription_rate_yoy_change"),
    )

    return {
        "school_name": latest["school_name_clean"],
        "phase": latest["phase_normalised"],
        "school_status": latest["school_status"],
        "is_active": latest["is_active"],
        "school_status_description": latest["school_status_description"],
        "prediction": {
            "ballot_risk_level": latest.get("ballot_risk_level"),
            "risk_explanation": risk_explanation,
            "basis": {
                "ballot_occurrences_last_3yr": latest.get("ballot_occurrences_last_3yr"),
                "ballot_occurrences_last_5yr": latest.get("ballot_occurrences_last_5yr"),
                "subscription_rate_3yr_avg": latest.get("subscription_rate_3yr_avg"),
                "subscription_rate_5yr_avg": latest.get("subscription_rate_5yr_avg"),
                "subscription_rate_yoy_change": latest.get("subscription_rate_yoy_change"),
                "vacancy_3yr_avg": latest.get("vacancy_3yr_avg"),
                "vacancy_yoy_change": latest.get("vacancy_yoy_change"),
                "reference_year": latest.get("registration_year"),
            },
            "disclaimer": (
                "This is a heuristic assessment based on historical data. "
                "ML-based probability prediction will be available in a future release."
            ),
        },
        "history": [
            {
                "registration_year": r["registration_year"],
                "vacancy": r.get("vacancy"),
                "applied": r.get("applied"),
                "taken": r.get("taken"),
                "subscription_rate": r.get("subscription_rate"),
                "ballot_scenario_code": r.get("ballot_scenario_code"),
                "ballot_chance_pct": r.get("ballot_chance_pct"),
                "ballot_risk_level": r.get("ballot_risk_level"),
            }
            for r in history_rows
        ],
    }