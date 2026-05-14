"""
routers/predict.py

GET /predict — returns structured ballot risk assessment for a
specific school and phase based on historical data.

Surfaces pre-computed ballot_risk_level and trend features from
mart_school_analysis with a templated risk_explanation string.
ML-based prediction is deferred to Week 3.

No is_active filter — historical data for inactive schools
(merged, relocated) is valid and surfaces useful context to parents.

Validation:
  - school_name: required
  - phase: required, must be one of 2B, 2C, 2C(S), 3
  - school not found: HTTP 404
  - phase out of scope: HTTP 422
"""

from fastapi import APIRouter, Query, HTTPException
from api.models.predict import PredictResponse
from api.services.predict import get_prediction
from api.constants import VALID_PHASES

router = APIRouter(prefix="/predict", tags=["Predict"])


@router.get("", response_model=PredictResponse)
async def predict(
    school_name: str = Query(description="Full school name e.g. ADMIRALTY PRIMARY SCHOOL"),
    phase: str = Query(description="Phase to predict: 2B, 2C, 2C(S), 3"),
):
    # -----------------------------------------------------------------------
    # Validation — phase scope check
    # Phases 1 and 2A are not supported in this iteration.
    # Frontend should prevent these from being passed, but external
    # callers receive a clear 422 with an explanatory message.
    # -----------------------------------------------------------------------
    school_name = school_name.upper()
    phase = phase.upper()
    if phase not in VALID_PHASES:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Phase '{phase}' is not supported. "
                f"Supported phases are: {', '.join(sorted(VALID_PHASES))}. "
                f"Phases 1 and 2A are excluded from ballot prediction in this iteration."
            )
        )

    result = get_prediction(school_name=school_name, phase=phase)

    # -----------------------------------------------------------------------
    # School not found — no rows returned from mart for this school-phase
    # combination. Could mean: school name is wrong, school has no data
    # for this phase, or school predates mart coverage.
    # -----------------------------------------------------------------------
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"No prediction data found for '{school_name}' in phase '{phase}'. "
                f"Check the school name matches exactly e.g. 'ADMIRALTY PRIMARY SCHOOL'."
            )
        )

    return PredictResponse(**result)