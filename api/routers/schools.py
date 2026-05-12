"""
routers/schools.py

GET /schools — returns active primary schools with their stable attributes.

Supports optional filtering by zone_code, dgp_code, type_code,
nature_code, session_code, sap_ind, autonomous_ind, gifted_ind.

At least one filter is not required here — /schools is a general
lookup endpoint. Filter requirements are enforced on /recommend.
"""

from fastapi import APIRouter, Query
from google.cloud import bigquery

from api.models.schools import SchoolRecord, SchoolsResponse
from api.services.bigquery import run_query, get_dataset

router = APIRouter(prefix="/schools", tags=["Schools"])   

@router.get("", response_model=SchoolsResponse)
async def get_schools(
    zone_code: str | None = Query(default=None, description="Filter by zone e.g. NORTH, SOUTH, EAST, WEST"),
    dgp_code: str | None = Query(default=None, description="Filter by Development Guide Plan code e.g. ADMIRALTY"),
    type_code: str | None = Query(default=None, description="Filter by school type e.g. GOVERNMENT, GOVERNMENT-AIDED"),
    nature_code: str | None = Query(default=None, description="Filter by school nature e.g. CO-ED, BOYS, GIRLS"),
    # session_code: str | None = Query(default=None, description="Filter by session e.g. SINGLE SESSION"),
    sap_ind: bool | None = Query(default=None, description="Filter by SAP school indicator: true or false"),
    autonomous_ind: bool | None = Query(default=None, description="Filter by autonomous school indicator: true or false"),
    gifted_ind: bool | None = Query(default=None, description="Filter by gifted programme indicator: true or false"),
    ip_ind: bool | None = Query(default=None, description="Filter by Integration Programme indicator: true or false")
):

    dataset = get_dataset()

    # ---------------------------------------------------------------------------
    # Build parameterised WHERE clauses dynamically based on provided filters.
    #
    # Each optional filter appends a condition and a corresponding
    # ScalarQueryParameter. Using UPPER() on both sides of the comparison
    # ensures case-insensitive matching — a caller passing "north" matches
    # a stored value of "NORTH".
    # ---------------------------------------------------------------------------
    conditions = ["is_active = TRUE"]
    params = []

    if zone_code:
        conditions.append("UPPER(zone_code) = UPPER(@zone_code)")
        params.append(bigquery.ScalarQueryParameter("zone_code", "STRING", zone_code))

    if dgp_code:
        conditions.append("UPPER(dgp_code) = UPPER(@dgp_code)")
        params.append(bigquery.ScalarQueryParameter("dgp_code", "STRING", dgp_code))

    if type_code:
        conditions.append("UPPER(type_code) = UPPER(@type_code)")
        params.append(bigquery.ScalarQueryParameter("type_code", "STRING", type_code))

    if nature_code:
        conditions.append("UPPER(nature_code) = UPPER(@nature_code)")
        params.append(bigquery.ScalarQueryParameter("nature_code", "STRING", nature_code))

    # if session_code:
    #     conditions.append("UPPER(session_code) = UPPER(@session_code)")
    #     params.append(bigquery.ScalarQueryParameter("session_code", "STRING", session_code))

    if sap_ind is not None:
        conditions.append("sap_ind = @sap_ind")
        params.append(bigquery.ScalarQueryParameter("sap_ind", "BOOL", sap_ind))

    if autonomous_ind is not None:
        conditions.append("autonomous_ind = @autonomous_ind")
        params.append(bigquery.ScalarQueryParameter("autonomous_ind", "BOOL", autonomous_ind))

    if gifted_ind is not None:
        conditions.append("gifted_ind = @gifted_ind")
        params.append(bigquery.ScalarQueryParameter("gifted_ind", "BOOL", gifted_ind))  

    if ip_ind is not None:
        conditions.append("ip_ind = @ip_ind")
        params.append(bigquery.ScalarQueryParameter("ip_ind", "BOOL", ip_ind))    

    where_clause = " AND ".join(conditions)

    sql = f"""
        SELECT
            school_key,
            school_name_clean        AS school_name,
            dgp_code,
            zone_code,
            type_code,
            nature_code,
            session_code,
            sap_ind,
            autonomous_ind,
            gifted_ind,
            ip_ind,
            mothertongue1_code,
            mothertongue2_code,
            mothertongue3_code,
            postal_code,
            school_status,
            school_status_description,
            is_active
        FROM `{dataset}.dim_school`
        WHERE {where_clause}
        ORDER BY school_name_clean ASC
    """

    rows = run_query(sql, params)

    return SchoolsResponse(
        count=len(rows),
        schools=[SchoolRecord(**row) for row in rows],
    )