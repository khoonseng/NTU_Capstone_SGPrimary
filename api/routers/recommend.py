"""
routers/recommend.py

GET /recommend — returns school recommendations based on location,
optional phase, and optional balloting filter.

Two response modes:
  Mode 1 (no phase): all phases, most recent year only
  Mode 2 (phase selected): single phase, last 3 years, with trend data

Validation rules enforced here before any BigQuery queries are made:
  - At least one of zone_code or dgp_code must be provided
  - has_balloting_3yr requires phase to be provided
"""

from fastapi import APIRouter, Query, HTTPException
from api.models.recommend import (
    RecommendResponseNoPhase,
    RecommendResponseWithPhase,
    QueryEchoNoPhase,
    QueryEchoWithPhase,
)
from api.services.recommend import (
    get_recommendations_no_phase,
    get_recommendations_with_phase,
)

router = APIRouter(prefix="/recommend", tags=["Recommend"])


@router.get("", response_model=RecommendResponseNoPhase | RecommendResponseWithPhase)
async def get_recommendations(
    zone_code: str | None = Query(default=None, description="Filter by zone: NORTH, SOUTH, EAST, WEST"),
    dgp_code: str | None = Query(default=None, description="Filter by Development Guide Plan code e.g. ADMIRALTY"),
    phase: str | None = Query(default=None, description="Filter by phase: 2B, 2C, 2C(S), 3"),
    has_balloting_3yr: bool | None = Query(default=None, description="Filter by balloting in last 3 years: true or false. Requires phase to be provided."),
    type_code: str | None = Query(default=None, description="Filter by school type e.g. GOVERNMENT, GOVERNMENT-AIDED"),
    nature_code: str | None = Query(default=None, description="Filter by school nature e.g. CO-ED, BOYS, GIRLS"),
    # session_code: str | None = Query(default=None, description="Filter by session e.g. SINGLE SESSION"),
    sap_ind: bool | None = Query(default=None, description="Filter by SAP school indicator: true or false"),
    autonomous_ind: bool | None = Query(default=None, description="Filter by autonomous school indicator: true or false"),
    gifted_ind: bool | None = Query(default=None, description="Filter by gifted programme indicator: true or false"),
    ip_ind: bool | None = Query(default=None, description="Filter by Integrated Programme indicator: true or false"),
):
    # -----------------------------------------------------------------------
    # Validation — enforce location and parameter dependency rules
    # -----------------------------------------------------------------------
    if not zone_code and not dgp_code:
        raise HTTPException(
            status_code=422,
            detail="At least one of zone_code or dgp_code must be provided."
        )

    if has_balloting_3yr is not None and not phase:
        raise HTTPException(
            status_code=422,
            detail="phase is required when has_balloting_3yr is provided."
        )

    # -----------------------------------------------------------------------
    # Route to the correct service function based on whether phase is provided
    # -----------------------------------------------------------------------
    if not phase:
        recommendations = get_recommendations_no_phase(
            zone_code=zone_code,
            dgp_code=dgp_code,
            type_code=type_code,
            nature_code=nature_code,
            # session_code=session_code,
            sap_ind=sap_ind,
            autonomous_ind=autonomous_ind,
            gifted_ind=gifted_ind,
            ip_ind=ip_ind,
        )
        return RecommendResponseNoPhase(
            query=QueryEchoNoPhase(
                zone_code=zone_code,
                dgp_code=dgp_code,
            ),
            count=len(recommendations),
            recommendations=recommendations,
        )

    else:
        recommendations = get_recommendations_with_phase(
            zone_code=zone_code,
            dgp_code=dgp_code,
            phase=phase,
            has_balloting_3yr=has_balloting_3yr,
            type_code=type_code,
            nature_code=nature_code,
            # session_code=session_code,
            sap_ind=sap_ind,
            autonomous_ind=autonomous_ind,
            gifted_ind=gifted_ind,
            ip_ind=ip_ind,
        )
        return RecommendResponseWithPhase(
            query=QueryEchoWithPhase(
                zone_code=zone_code,
                dgp_code=dgp_code,
                phase=phase,
                has_balloting_3yr=has_balloting_3yr,
            ),
            count=len(recommendations),
            recommendations=recommendations,
        )