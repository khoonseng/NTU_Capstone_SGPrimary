"""
routers/school_detail.py

GET /schools/{school_name} — returns full detail for a single school.

Path parameter school_name must match the canonical school name
exactly e.g. 'ADMIRALTY PRIMARY SCHOOL'. Case-insensitive matching
is handled in the service layer via UPPER(TRIM(...)).

No phase or year filtering — this endpoint returns static school
attributes only. Ballot history is available via /predict and
/recommend.

Error responses:
    404 — school name not found in dim_school
"""

from fastapi import APIRouter, HTTPException
from api.models.school_detail import SchoolDetailResponse
from api.services.school_detail import get_school_detail

router = APIRouter(prefix="/schools", tags=["Schools"])


@router.get("/{school_name}", response_model=SchoolDetailResponse)
async def get_school_by_name(school_name: str):
    result = get_school_detail(school_name=school_name)

    if result is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"School '{school_name}' not found. "
                f"Check the name matches exactly e.g. 'ADMIRALTY PRIMARY SCHOOL'."
            )
        )

    return SchoolDetailResponse(**result)
