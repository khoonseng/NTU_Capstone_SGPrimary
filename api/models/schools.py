"""
models/schools.py

Pydantic response models for the /schools endpoint.

These define the exact JSON shape returned to the caller.
Pydantic validates and serialises the BigQuery result dicts
into these models before the response is sent.
"""

from pydantic import BaseModel


class SchoolRecord(BaseModel):
    school_key: str
    school_name: str
    dgp_code: str | None
    zone_code: str | None
    type_code: str | None
    nature_code: str | None
    session_code: str | None
    sap_ind: bool | None
    autonomous_ind: bool | None
    gifted_ind: bool | None
    ip_ind: bool | None
    mothertongue1_code: str | None
    mothertongue2_code: str | None
    mothertongue3_code: str | None
    postal_code: int | None
    school_status: str
    school_status_description: str
    is_active: bool


class SchoolsResponse(BaseModel):
    count: int
    schools: list[SchoolRecord]