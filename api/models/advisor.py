"""
models/advisor.py

Pydantic request and response models for the POST /advisor endpoint.
"""

from pydantic import BaseModel, Field


class AdvisorRequest(BaseModel):
    question: str = Field(min_length=3, max_length=500)
    school_name: str | None = None
    phase: str | None = None
    session_id: str | None = None
    conversation_history: list[dict] | None = None  # unused in Week 4, wired for Week 5


class SourceDocument(BaseModel):
    topic: str
    source_file: str
    source_url: str | None = None


class AdvisorResponse(BaseModel):
    answer: str
    sources: list[SourceDocument]
    school_context_used: bool
    disclaimer: str