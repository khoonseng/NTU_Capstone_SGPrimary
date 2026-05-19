"""
models/school_detail.py

Pydantic response model for GET /schools/{school_name}.

Combines dim_school (stable attributes + lifecycle) and
dim_school_generalinfo (operational attributes) into one
response. All generalinfo fields are optional — merged schools
have no generalinfo record.
"""

from pydantic import BaseModel


class SchoolDetailResponse(BaseModel):
    # ── Identity ────────────────────────────────────────────────────────
    school_key: str
    school_name: str

    # ── Overview [dim_school] ────────────────────────────────────────────
    address: str | None
    postal_code: int | None
    zone_code: str | None
    dgp_code: str | None
    type_code: str | None
    nature_code: str | None
    session_code: str | None
    mothertongue1_code: str | None
    mothertongue2_code: str | None
    mothertongue3_code: str | None
    sap_ind: bool | None
    autonomous_ind: bool | None
    gifted_ind: bool | None
    ip_ind: bool | None

    # ── Lifecycle [dim_school] ───────────────────────────────────────────
    is_active: bool
    school_status: str
    school_status_description: str
    inactive_from_year: int | None
    inactive_to_year: int | None
    merged_into: str | None

    # ── Contact [dim_school_generalinfo] ────────────────────────────────
    url_address: str | None
    email_address: str | None
    telephone_no: str | None
    telephone_no_2: str | None
    fax_no: str | None
    fax_no_2: str | None

    # ── Transport [dim_school_generalinfo] ───────────────────────────────
    mrt_desc: str | None
    bus_desc: str | None

    # ── Leadership [dim_school_generalinfo] ──────────────────────────────
    principal_name: str | None
    first_vp_name: str | None
    second_vp_name: str | None
    third_vp_name: str | None
    fourth_vp_name: str | None
    fifth_vp_name: str | None
    sixth_vp_name: str | None
