"""
models/recommend.py

Pydantic response models for the /recommend endpoint.

Two response modes depending on whether phase is provided:
  Mode 1 (no phase): RecommendResponseNoPhase
    - One SchoolSummary per school, phases nested as list of PhaseLatestYear
    - Most recent completed year + 2026 if available per phase
    - No trend data

  Mode 2 (phase selected): RecommendResponseWithPhase
    - One SchoolRecommendation per school-phase
    - Last 3 historical years + 2026 if available
    - Includes trend block and reference_years

BallotYearRecord is shared across both modes — represents one year's
balloting result for a given school-phase.
"""

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Shared — one year's balloting result for a school-phase
# ---------------------------------------------------------------------------
class BallotYearRecord(BaseModel):
    registration_year: int | None
    total_vacancy: int | None
    vacancy: int | None
    applied: int | None
    taken: int | None
    remaining_places: int | None
    subscription_rate: float | None
    ballot_scenario_code: str | None
    ballot_description: str | None
    ballot_applicants: int | None
    ballot_vacancies: int | None
    ballot_chance_pct: float | None
    ballot_citizen_group: str | None
    ballot_distance_band: str | None
    ballot_risk_level: str | None
    is_current_year: bool


# ---------------------------------------------------------------------------
# Shared — stable school attributes embedded in every recommendation
# ---------------------------------------------------------------------------
class SchoolAttributes(BaseModel):
    type_code: str | None
    nature_code: str | None
    # session_code: str | None
    sap_ind: bool | None
    autonomous_ind: bool | None
    gifted_ind: bool | None
    ip_ind: bool | None
    mothertongue1_code: str | None
    mothertongue2_code: str | None
    mothertongue3_code: str | None
    postal_code: int | None


# ---------------------------------------------------------------------------
# Mode 1 — no phase selected
# One PhaseLatestYear per phase nested inside SchoolSummary
# ---------------------------------------------------------------------------
class PhaseLatestYear(BaseModel):
    phase: str
    years: list[BallotYearRecord]           # most recent completed year + 2026 if available


class SchoolSummary(BaseModel):
    school_name: str
    dgp_code: str | None
    zone_code: str | None
    school_attributes: SchoolAttributes
    school_status: str
    school_status_description: str
    phases: list[PhaseLatestYear]


class QueryEchoNoPhase(BaseModel):
    zone_code: str | None
    dgp_code: str | None
    phase: None = None
    has_balloting_3yr: None = None


class RecommendResponseNoPhase(BaseModel):
    query: QueryEchoNoPhase
    count: int                              # number of unique schools returned
    recommendations: list[SchoolSummary]


# ---------------------------------------------------------------------------
# Mode 2 — phase selected
# One SchoolRecommendation per school (for the selected phase)
# ---------------------------------------------------------------------------
class TrendData(BaseModel):
    ballot_occurrences_last_3yr: int | None
    ballot_occurrences_last_5yr: int | None
    subscription_rate_3yr_avg: float | None
    subscription_rate_5yr_avg: float | None
    subscription_rate_yoy_change: float | None
    vacancy_3yr_avg: float | None
    vacancy_yoy_change: int | None


class SchoolRecommendation(BaseModel):
    school_name: str
    dgp_code: str | None
    zone_code: str | None
    phase: str
    school_attributes: SchoolAttributes
    school_status: str
    school_status_description: str
    latest_year: BallotYearRecord           # most recent completed year
    trend: TrendData
    history: list[BallotYearRecord]         # last 3 years + 2026 if available
    reference_years: list[int]              # derived from non-current-year history rows


class QueryEchoWithPhase(BaseModel):
    zone_code: str | None
    dgp_code: str | None
    phase: str
    has_balloting_3yr: bool | None


class RecommendResponseWithPhase(BaseModel):
    query: QueryEchoWithPhase
    count: int                              # number of unique schools returned
    recommendations: list[SchoolRecommendation]