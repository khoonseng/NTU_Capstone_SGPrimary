"""
models/metadata.py

Pydantic response models for the /metadata endpoint.

Returns lookup values for all dropdown filters used in the frontend.
Structured as a single response object so the frontend makes one API
call on app load rather than one call per filter type.

estate_by_zone is a dict keyed by zone_code — enables the frontend
to implement cascading zone → estate filtering without additional
API calls. Estates within each zone are sorted alphabetically.
"""

from pydantic import BaseModel


class MetadataResponse(BaseModel):
    zones: list[str]                        # distinct zone_code values
    estates_by_zone: dict[str, list[str]]   # zone_code → sorted list of dgp_code
    all_estates: list[str]                  # all dgp_code values, sorted — for when no zone selected
    type_codes: list[str]                   # distinct type_code values
    nature_codes: list[str]                 # distinct nature_code values
