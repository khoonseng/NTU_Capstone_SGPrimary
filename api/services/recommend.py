"""
services/recommend.py

Business logic for the /recommend endpoint.

Two public functions:
  get_recommendations_no_phase()   — Mode 1, no phase selected
  get_recommendations_with_phase() — Mode 2, phase selected

Both functions compute current_year = date.today().year at call time —
not at module load time — so the value stays accurate across calendar
year boundaries without requiring an application restart.

Query strategy:
  UNION ALL separates historical rows (registration_year < current_year)
  from current year rows (registration_year = current_year).
  This ensures "most recent completed year" never includes the current
  calendar year, even if partial 2026 data exists in the mart.

  Historical CTE: ROW_NUMBER() ranks rows DESC, capped at 1 (Mode 1)
  or 3 (Mode 2) most recent completed years.
  Current year CTE: fetches current year rows independently.
  Python assembly appends a null sentinel if no current year rows exist.
"""

from datetime import date
from google.cloud import bigquery
from api.services.bigquery import run_query, get_dataset


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _get_current_year() -> int:
    """
    Returns the current calendar year, computed at call time.

    Deliberately not cached or stored at module level — this ensures
    the value is always accurate across calendar year boundaries
    without requiring an application restart.
    """
    return date.today().year


def _build_location_conditions(
    zone_code: str | None,
    dgp_code: str | None,
    params: list,
) -> list[str]:
    """
    Builds WHERE conditions and appends BigQuery params for location filters.
    zone_code and dgp_code are AND-combined when both are provided.
    """
    conditions = []

    if zone_code:
        conditions.append("UPPER(m.zone_code) = UPPER(@zone_code)")
        params.append(bigquery.ScalarQueryParameter("zone_code", "STRING", zone_code))

    if dgp_code:
        conditions.append("UPPER(m.dgp_code) = UPPER(@dgp_code)")
        params.append(bigquery.ScalarQueryParameter("dgp_code", "STRING", dgp_code))

    return conditions


def _build_attribute_conditions(
    type_code: str | None,
    nature_code: str | None,
    # session_code: str | None,
    sap_ind: bool | None,
    autonomous_ind: bool | None,
    gifted_ind: bool | None,
    ip_ind: bool | None,
    params: list,
) -> list[str]:
    """
    Builds WHERE conditions and appends BigQuery params for school
    attribute filters. All optional — only appended when provided.
    """
    conditions = []

    if type_code:
        conditions.append("UPPER(m.type_code) = UPPER(@type_code)")
        params.append(bigquery.ScalarQueryParameter("type_code", "STRING", type_code))

    if nature_code:
        conditions.append("UPPER(m.nature_code) = UPPER(@nature_code)")
        params.append(bigquery.ScalarQueryParameter("nature_code", "STRING", nature_code))

    # if session_code:
    #     conditions.append("UPPER(m.session_code) = UPPER(@session_code)")
    #     params.append(bigquery.ScalarQueryParameter("session_code", "STRING", session_code))

    if sap_ind is not None:
        conditions.append("m.sap_ind = @sap_ind")
        params.append(bigquery.ScalarQueryParameter("sap_ind", "BOOL", sap_ind))

    if autonomous_ind is not None:
        conditions.append("m.autonomous_ind = @autonomous_ind")
        params.append(bigquery.ScalarQueryParameter("autonomous_ind", "BOOL", autonomous_ind))

    if gifted_ind is not None:
        conditions.append("m.gifted_ind = @gifted_ind")
        params.append(bigquery.ScalarQueryParameter("gifted_ind", "BOOL", gifted_ind))

    if ip_ind is not None:
        conditions.append("m.ip_ind = @ip_ind")
        params.append(bigquery.ScalarQueryParameter("ip_ind", "BOOL", ip_ind))

    return conditions


def _null_current_year_row(current_year: int) -> dict:
    """
    Returns a null-filled sentinel row representing the current year
    when no current year data exists in mart_school_analysis yet.

    Accepts current_year as a parameter — never reads a module-level
    constant — so the value is always consistent with the calling
    function's computed current_year.
    """
    return {
        "registration_year": current_year,
        "total_vacancy": None,
        "vacancy": None,
        "applied": None,
        "taken": None,
        "remaining_places": None,
        "subscription_rate": None,
        "ballot_scenario_code": None,
        "ballot_description": None,
        "ballot_applicants": None,
        "ballot_vacancies": None,
        "ballot_chance_pct": None,
        "ballot_citizen_group": None,
        "ballot_distance_band": None,
        "ballot_risk_level": None,
        "is_current_year": True,
    }


def _to_ballot_year(row: dict, is_current_year: bool) -> dict:
    """
    Maps a BigQuery result row to a BallotYearRecord-compatible dict.
    """
    return {
        "registration_year": row.get("registration_year"),
        "total_vacancy": row.get("total_vacancy"),
        "vacancy": row.get("vacancy"),
        "applied": row.get("applied"),
        "taken": row.get("taken"),
        "remaining_places": row.get("remaining_places"),
        "subscription_rate": row.get("subscription_rate"),
        "ballot_scenario_code": row.get("ballot_scenario_code"),
        "ballot_description": row.get("ballot_description"),
        "ballot_applicants": row.get("ballot_applicants"),
        "ballot_vacancies": row.get("ballot_vacancies"),
        "ballot_chance_pct": row.get("ballot_chance_pct"),
        "ballot_citizen_group": row.get("ballot_citizen_group"),
        "ballot_distance_band": row.get("ballot_distance_band"),
        "ballot_risk_level": row.get("ballot_risk_level"),
        "is_current_year": is_current_year,
    }


# ---------------------------------------------------------------------------
# Mode 1 — no phase selected
# ---------------------------------------------------------------------------

def get_recommendations_no_phase(
    zone_code: str | None,
    dgp_code: str | None,
    type_code: str | None,
    nature_code: str | None,
    # session_code: str | None,
    sap_ind: bool | None,
    autonomous_ind: bool | None,
    gifted_ind: bool | None,
    ip_ind: bool | None,
) -> list[dict]:
    """
    Mode 1: no phase selected.

    Returns one dict per school with all phases nested.
    Each phase contains exactly:
      - 1 most recent completed year (registration_year < current_year)
      - 1 current year row (registration_year = current_year, or null sentinel)

    current_year computed at call time via _get_current_year().
    """
    current_year = _get_current_year()
    dataset = get_dataset()

    # Build shared params list — passed into both CTEs via same param set
    # since BigQuery parameterised queries share params across the full SQL
    params = []
    conditions = ["m.is_active = TRUE"]
    conditions += _build_location_conditions(zone_code, dgp_code, params)
    conditions += _build_attribute_conditions(
        type_code, nature_code, #session_code,
        sap_ind, autonomous_ind, gifted_ind, ip_ind, params
    )
    where_clause = " AND ".join(conditions)

    sql = f"""
        -- Most recent completed year per school-phase
        -- Excludes current year rows so "most recent" is always a
        -- fully completed registration year
        WITH historical AS (
            SELECT
                m.school_name_clean,
                m.dgp_code,
                m.zone_code,
                m.type_code,
                m.nature_code,
                m.session_code,
                m.sap_ind,
                m.autonomous_ind,
                m.gifted_ind,
                m.ip_ind,
                m.mothertongue1_code,
                m.mothertongue2_code,
                m.mothertongue3_code,
                m.postal_code,
                m.school_status,
                m.school_status_description,
                m.phase_normalised,
                m.registration_year,
                m.total_vacancy,
                m.vacancy,
                m.applied,
                m.taken,
                m.remaining_places,
                m.subscription_rate,
                m.ballot_scenario_code,
                m.ballot_description,
                m.ballot_applicants,
                m.ballot_vacancies,
                m.ballot_chance_pct,
                m.ballot_citizen_group,
                m.ballot_distance_band,
                m.ballot_risk_level,
                ROW_NUMBER() OVER (
                    PARTITION BY m.school_name_clean, m.phase_normalised
                    ORDER BY m.registration_year DESC
                ) AS row_rank
            FROM `{dataset}.mart_school_analysis` m
            WHERE {where_clause}
              AND m.registration_year < {current_year}
        ),

        -- Current year rows — independent of historical ranking
        -- Will be empty if current year registration has not started
        current_yr AS (
            SELECT
                m.school_name_clean,
                m.dgp_code,
                m.zone_code,
                m.type_code,
                m.nature_code,
                m.session_code,
                m.sap_ind,
                m.autonomous_ind,
                m.gifted_ind,
                m.ip_ind,
                m.mothertongue1_code,
                m.mothertongue2_code,
                m.mothertongue3_code,
                m.postal_code,
                m.school_status,
                m.school_status_description,
                m.phase_normalised,
                m.registration_year,
                m.total_vacancy,
                m.vacancy,
                m.applied,
                m.taken,
                m.remaining_places,
                m.subscription_rate,
                m.ballot_scenario_code,
                m.ballot_description,
                m.ballot_applicants,
                m.ballot_vacancies,
                m.ballot_chance_pct,
                m.ballot_citizen_group,
                m.ballot_distance_band,
                m.ballot_risk_level,
                1 AS row_rank
            FROM `{dataset}.mart_school_analysis` m
            WHERE {where_clause}
              AND m.registration_year = {current_year}
        )

        SELECT * FROM historical WHERE row_rank = 1
        UNION ALL
        SELECT * FROM current_yr
        ORDER BY
            dgp_code ASC,
            school_name_clean ASC,
            phase_normalised ASC,
            registration_year DESC
    """

    rows = run_query(sql, params)
    return _assemble_no_phase(rows, current_year)


def _assemble_no_phase(rows: list[dict], current_year: int) -> list[dict]:
    """
    Assembles BigQuery rows into the Mode 1 nested structure.

    Groups rows by school then phase. For each phase:
      - Separates current year row from the most recent completed year row
      - Appends null sentinel if no current year row exists

    current_year passed in as parameter — consistent with the calling
    function's computed value.
    """
    schools: dict[str, dict] = {}
    school_order: list[str] = []

    for row in rows:
        school_name = row["school_name_clean"]
        phase = row["phase_normalised"]
        year = row["registration_year"]

        if school_name not in schools:
            school_order.append(school_name)
            schools[school_name] = {
                "school_name": school_name,
                "dgp_code": row["dgp_code"],
                "zone_code": row["zone_code"],
                "school_attributes": {
                    "type_code": row["type_code"],
                    "nature_code": row["nature_code"],
                    # "session_code": row["session_code"],
                    "sap_ind": row["sap_ind"],
                    "autonomous_ind": row["autonomous_ind"],
                    "gifted_ind": row["gifted_ind"],
                    "ip_ind": row["ip_ind"],
                    "mothertongue1_code": row["mothertongue1_code"],
                    "mothertongue2_code": row["mothertongue2_code"],
                    "mothertongue3_code": row["mothertongue3_code"],
                    "postal_code": row["postal_code"],
                },
                "school_status": row["school_status"],
                "school_status_description": row["school_status_description"],
                "phases": {},
                "phase_order": [],
            }

        school = schools[school_name]

        if phase not in school["phases"]:
            school["phase_order"].append(phase)
            school["phases"][phase] = {
                "phase": phase,
                "years": [],
                "has_current_year": False,
            }

        is_current = (year == current_year)
        if is_current:
            school["phases"][phase]["has_current_year"] = True

        school["phases"][phase]["years"].append(_to_ballot_year(row, is_current))

    # Append null sentinel for phases missing current year data
    for school_name in school_order:
        school = schools[school_name]
        for phase in school["phase_order"]:
            if not school["phases"][phase]["has_current_year"]:
                school["phases"][phase]["years"].append(
                    _null_current_year_row(current_year)
                )

    # Flatten to list format expected by Pydantic models
    result = []
    for school_name in school_order:
        school = schools[school_name]
        result.append({
            "school_name": school["school_name"],
            "dgp_code": school["dgp_code"],
            "zone_code": school["zone_code"],
            "school_attributes": school["school_attributes"],
            "school_status": school["school_status"],
            "school_status_description": school["school_status_description"],
            "phases": [
                {"phase": p, "years": school["phases"][p]["years"]}
                for p in school["phase_order"]
            ],
        })

    return result


# ---------------------------------------------------------------------------
# Mode 2 — phase selected [revised logic]
# ---------------------------------------------------------------------------
def get_recommendations_with_phase(
    zone_code: str | None,
    dgp_code: str | None,
    phase: str,
    has_balloting_3yr: bool | None,
    type_code: str | None,
    nature_code: str | None,
    # session_code: str | None,
    sap_ind: bool | None,
    autonomous_ind: bool | None,
    gifted_ind: bool | None,
    ip_ind: bool | None,
) -> list[dict]:
    """
    Mode 2: phase selected.

    Returns one dict per school for the selected phase.
    Each school includes:
      - Last 3 most recent completed years (registration_year < current_year)
      - Current year row (registration_year = current_year, or null sentinel)
      - Trend data from the most recent completed year row
      - reference_years derived from historical rows in Python assembly

    has_balloting_3yr filter logic:
      Qualifying schools are determined by evaluating ballot_occurrences_last_3yr
      on the most recent completed year row ONLY (row_rank = 1 in qualifying_schools CTE).
      Once a school qualifies, all 3 historical years are fetched unconditionally.
      Current year rows are only included for qualifying schools.

    has_balloting_3yr=True  → most recent completed year ballot_occurrences_last_3yr > 0
    has_balloting_3yr=False → most recent completed year ballot_occurrences_last_3yr = 0
    has_balloting_3yr=None  → no balloting filter applied, all schools returned
    """
    current_year = _get_current_year()
    dataset = get_dataset()

    params = []
    conditions = ["m.is_active = TRUE"]
    conditions += _build_location_conditions(zone_code, dgp_code, params)
    conditions += _build_attribute_conditions(
        type_code, nature_code, #session_code,
        sap_ind, autonomous_ind, gifted_ind, ip_ind, params
    )

    conditions.append("UPPER(m.phase_normalised) = UPPER(@phase)")
    params.append(bigquery.ScalarQueryParameter("phase", "STRING", phase))

    where_clause = " AND ".join(conditions)

    # Balloting condition applied to the most recent completed year row only
    # in the qualifying_schools CTE — not to all historical rows
    if has_balloting_3yr is True:
        balloting_condition = "AND ballot_occurrences_last_3yr > 0"
    elif has_balloting_3yr is False:
        balloting_condition = "AND ballot_occurrences_last_3yr = 0"
    else:
        balloting_condition = ""

    sql = f"""
        -- ---------------------------------------------------------------
        -- Step 1: Identify qualifying schools
        --
        -- Evaluates has_balloting_3yr filter on the most recent completed
        -- year row per school only (row_rank = 1).
        -- When has_balloting_3yr is None, balloting_condition is empty
        -- and all schools matching location/attribute filters qualify.
        -- ---------------------------------------------------------------
        WITH qualifying_schools AS (
            SELECT school_name_clean
            FROM (
                SELECT
                    m.school_name_clean,
                    m.ballot_occurrences_last_3yr,
                    ROW_NUMBER() OVER (
                        PARTITION BY m.school_name_clean
                        ORDER BY m.registration_year DESC
                    ) AS row_rank
                FROM `{dataset}.mart_school_analysis` m
                WHERE {where_clause}
                  AND m.registration_year < {current_year}
            )
            WHERE row_rank = 1
              {balloting_condition}
        ),

        -- ---------------------------------------------------------------
        -- Step 2: Fetch last 3 completed years for qualifying schools
        --
        -- INNER JOIN against qualifying_schools ensures only schools
        -- that passed the balloting filter in Step 1 are included.
        -- All 3 historical rows are fetched unconditionally — the
        -- balloting filter is not re-applied here.
        -- ---------------------------------------------------------------
        historical AS (
            SELECT
                m.school_name_clean,
                m.dgp_code,
                m.zone_code,
                m.type_code,
                m.nature_code,
                m.session_code,
                m.sap_ind,
                m.autonomous_ind,
                m.gifted_ind,
                m.ip_ind,
                m.mothertongue1_code,
                m.mothertongue2_code,
                m.mothertongue3_code,
                m.postal_code,
                m.school_status,
                m.school_status_description,
                m.phase_normalised,
                m.registration_year,
                m.total_vacancy,
                m.vacancy,
                m.applied,
                m.taken,
                m.remaining_places,
                m.subscription_rate,
                m.ballot_scenario_code,
                m.ballot_description,
                m.ballot_applicants,
                m.ballot_vacancies,
                m.ballot_chance_pct,
                m.ballot_citizen_group,
                m.ballot_distance_band,
                m.ballot_risk_level,
                m.ballot_occurrences_last_3yr,
                m.ballot_occurrences_last_5yr,
                m.subscription_rate_3yr_avg,
                m.subscription_rate_5yr_avg,
                m.subscription_rate_yoy_change,
                m.vacancy_3yr_avg,
                m.vacancy_yoy_change,
                ROW_NUMBER() OVER (
                    PARTITION BY m.school_name_clean
                    ORDER BY m.registration_year DESC
                ) AS row_rank
            FROM `{dataset}.mart_school_analysis` m
            INNER JOIN qualifying_schools q
                ON m.school_name_clean = q.school_name_clean
            WHERE {where_clause}
              AND m.registration_year < {current_year}
        ),

        -- ---------------------------------------------------------------
        -- Step 3: Fetch current year rows for qualifying schools only
        --
        -- INNER JOIN against qualifying_schools ensures current year
        -- rows are only included for schools that passed the balloting
        -- filter. Empty if current year registration has not started.
        -- ---------------------------------------------------------------
        current_yr AS (
            SELECT
                m.school_name_clean,
                m.dgp_code,
                m.zone_code,
                m.type_code,
                m.nature_code,
                m.session_code,
                m.sap_ind,
                m.autonomous_ind,
                m.gifted_ind,
                m.ip_ind,
                m.mothertongue1_code,
                m.mothertongue2_code,
                m.mothertongue3_code,
                m.postal_code,
                m.school_status,
                m.school_status_description,
                m.phase_normalised,
                m.registration_year,
                m.total_vacancy,
                m.vacancy,
                m.applied,
                m.taken,
                m.remaining_places,
                m.subscription_rate,
                m.ballot_scenario_code,
                m.ballot_description,
                m.ballot_applicants,
                m.ballot_vacancies,
                m.ballot_chance_pct,
                m.ballot_citizen_group,
                m.ballot_distance_band,
                m.ballot_risk_level,
                m.ballot_occurrences_last_3yr,
                m.ballot_occurrences_last_5yr,
                m.subscription_rate_3yr_avg,
                m.subscription_rate_5yr_avg,
                m.subscription_rate_yoy_change,
                m.vacancy_3yr_avg,
                m.vacancy_yoy_change,
                1 AS row_rank
            FROM `{dataset}.mart_school_analysis` m
            INNER JOIN qualifying_schools q
                ON m.school_name_clean = q.school_name_clean
            WHERE {where_clause}
              AND m.registration_year = {current_year}
        )

        SELECT * FROM historical WHERE row_rank <= 3
        UNION ALL
        SELECT * FROM current_yr
        ORDER BY
            dgp_code ASC,
            school_name_clean ASC,
            registration_year DESC
    """

    rows = run_query(sql, params)
    return _assemble_with_phase(rows, phase, current_year)


def _assemble_with_phase(rows: list[dict], phase: str, current_year: int) -> list[dict]:
    """
    Assembles BigQuery rows into the Mode 2 nested structure.

    Groups rows by school. For each school:
      - Separates current year row from historical rows
      - Most recent historical row drives latest_year and trend data
      - reference_years derived from historical row years only
      - Null sentinel appended if no current year row exists

    current_year passed in as parameter — consistent with calling
    function's computed value.
    """
    schools: dict[str, dict] = {}
    school_order: list[str] = []

    for row in rows:
        school_name = row["school_name_clean"]
        year = row["registration_year"]

        if school_name not in schools:
            school_order.append(school_name)
            schools[school_name] = {
                "school_name": school_name,
                "dgp_code": row["dgp_code"],
                "zone_code": row["zone_code"],
                "phase": phase,
                "school_attributes": {
                    "type_code": row["type_code"],
                    "nature_code": row["nature_code"],
                    # "session_code": row["session_code"],
                    "sap_ind": row["sap_ind"],
                    "autonomous_ind": row["autonomous_ind"],
                    "gifted_ind": row["gifted_ind"],
                    "ip_ind": row["ip_ind"],
                    "mothertongue1_code": row["mothertongue1_code"],
                    "mothertongue2_code": row["mothertongue2_code"],
                    "mothertongue3_code": row["mothertongue3_code"],
                    "postal_code": row["postal_code"],
                },
                "school_status": row["school_status"],
                "school_status_description": row["school_status_description"],
                "historical_rows": [],
                "current_year_row": None,
            }

        school = schools[school_name]

        if year == current_year:
            school["current_year_row"] = _to_ballot_year(row, True)
        else:
            school["historical_rows"].append(row)

    # Assemble final structure per school
    result = []
    for school_name in school_order:
        school = schools[school_name]
        historical = school["historical_rows"]

        # Most recent historical row drives latest_year and trend
        latest = historical[0] if historical else {}

        latest_year = _to_ballot_year(latest, False) if latest else None

        trend = {
            "ballot_occurrences_last_3yr": latest.get("ballot_occurrences_last_3yr"),
            "ballot_occurrences_last_5yr": latest.get("ballot_occurrences_last_5yr"),
            "subscription_rate_3yr_avg": latest.get("subscription_rate_3yr_avg"),
            "subscription_rate_5yr_avg": latest.get("subscription_rate_5yr_avg"),
            "subscription_rate_yoy_change": latest.get("subscription_rate_yoy_change"),
            "vacancy_3yr_avg": latest.get("vacancy_3yr_avg"),
            "vacancy_yoy_change": latest.get("vacancy_yoy_change"),
        }

        # History = all historical rows + current year row
        history = [_to_ballot_year(r, False) for r in historical]
        current_year_row = (
            school["current_year_row"]
            if school["current_year_row"] is not None
            else _null_current_year_row(current_year)
        )
        history.append(current_year_row)

        # reference_years from historical rows only — never includes current year
        reference_years = sorted(
            [r["registration_year"] for r in historical],
            reverse=True
        )

        result.append({
            "school_name": school["school_name"],
            "dgp_code": school["dgp_code"],
            "zone_code": school["zone_code"],
            "phase": school["phase"],
            "school_attributes": school["school_attributes"],
            "school_status": school["school_status"],
            "school_status_description": school["school_status_description"],
            "latest_year": latest_year,
            "trend": trend,
            "history": history,
            "reference_years": reference_years,
        })

    return result
