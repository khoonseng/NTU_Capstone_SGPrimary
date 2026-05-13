"""
models/predict.py

Pydantic response models for the /predict endpoint.

Response shape:
  - School identity and status
  - Prediction block: ballot_risk_level + trend features + templated explanation
  - History block: last 3 completed years, no current year sentinel
    (prediction is based on past data only)
"""

from pydantic import BaseModel


class PredictHistoryRecord(BaseModel):
    registration_year: int
    vacancy: int | None
    applied: int | None
    taken: int | None
    subscription_rate: float | None
    ballot_scenario_code: str | None
    ballot_chance_pct: float | None
    ballot_risk_level: str | None


class PredictionBasis(BaseModel):
    ballot_occurrences_last_3yr: int | None
    ballot_occurrences_last_5yr: int | None
    subscription_rate_3yr_avg: float | None
    subscription_rate_5yr_avg: float | None
    subscription_rate_yoy_change: float | None
    vacancy_3yr_avg: float | None
    vacancy_yoy_change: int | None
    reference_year: int | None              # most recent completed year driving the prediction


class Prediction(BaseModel):
    ballot_risk_level: str | None
    risk_explanation: str
    basis: PredictionBasis
    disclaimer: str


class PredictResponse(BaseModel):
    school_name: str
    phase: str
    school_status: str
    is_active: bool
    school_status_description: str
    prediction: Prediction
    history: list[PredictHistoryRecord]