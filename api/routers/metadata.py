"""
routers/metadata.py

GET /metadata — returns all dropdown filter values for the frontend.

No query parameters — returns the full metadata set in one call.
Frontend caches this for the session so BigQuery is queried once
per session, not once per page load.

No validation needed — this endpoint has no user inputs.
"""

from fastapi import APIRouter
from api.models.metadata import MetadataResponse
from api.services.metadata import get_metadata

router = APIRouter(prefix="/metadata", tags=["Metadata"])


@router.get("", response_model=MetadataResponse)
async def metadata():
    result = get_metadata()
    return MetadataResponse(**result)
