"""
services/school_detail.py

Business logic for GET /schools/{school_name}.

Joins dim_school and dim_school_generalinfo on school_key.
LEFT JOIN is used so merged schools (which have no generalinfo
record) still return a result — all generalinfo fields are NULL
for merged schools, which the Pydantic model handles correctly
via | None types.

Returns None if school not found — caller handles HTTP 404.
"""

from google.cloud import bigquery
from api.services.bigquery import run_query, get_dataset


def get_school_detail(school_name: str) -> dict | None:
    """
    Fetches combined dim_school + dim_school_generalinfo for one school.

    Args:
        school_name: canonical school name, case-insensitive matched

    Returns:
        Dict ready for SchoolDetailResponse, or None if not found.
    """
    dataset = get_dataset()

    params = [
        bigquery.ScalarQueryParameter("school_name", "STRING", school_name.upper().strip()),
    ]

    sql = f"""
        SELECT
            s.school_key,
            s.school_name_clean                 AS school_name,

            -- Overview
            s.address,
            s.postal_code,
            s.zone_code,
            s.dgp_code,
            s.type_code,
            s.nature_code,
            s.session_code,
            s.mothertongue1_code,
            s.mothertongue2_code,
            s.mothertongue3_code,
            s.sap_ind,
            s.autonomous_ind,
            s.gifted_ind,
            s.ip_ind,

            -- Lifecycle
            s.is_active,
            s.school_status,
            s.school_status_description,
            s.inactive_from_year,
            s.inactive_to_year,
            s.merged_into,

            -- Contact (NULL for merged schools)
            g.url_address,
            g.email_address,
            g.telephone_no,
            g.telephone_no_2,
            g.fax_no,
            g.fax_no_2,

            -- Transport (NULL for merged schools)
            g.mrt_desc,
            g.bus_desc,

            -- Leadership (NULL for merged schools)
            g.principal_name,
            g.first_vp_name,
            g.second_vp_name,
            g.third_vp_name,
            g.fourth_vp_name,
            g.fifth_vp_name,
            g.sixth_vp_name

        FROM `{dataset}.dim_school` s
        LEFT JOIN `{dataset}.dim_school_generalinfo` g
            ON s.school_key = g.school_key
        WHERE UPPER(TRIM(s.school_name_clean)) = @school_name
        LIMIT 1
    """

    rows = run_query(sql, params)

    if not rows:
        return None

    return dict(rows[0])
