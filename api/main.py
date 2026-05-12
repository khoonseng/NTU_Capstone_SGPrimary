"""
main.py

FastAPI application entry point for the SGPrimary API.

Registers all routers and defines global exception handlers
to ensure consistent error response shapes across all endpoints.
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from api.routers import schools, recommend, predict


app = FastAPI(
    title="SGPrimary API",
    description="P1 Ballot Insights and School Recommendation Engine for Singapore parents.",
    version="0.1.0",
)


# ---------------------------------------------------------------------------
# Global exception handlers
#
# FastAPI's default 422 validation error response is verbose and technical.
# This handler intercepts it and returns a clean, consistent shape:
#   {"error": "Invalid request parameters", "detail": [...]}
#
# All other unhandled exceptions return a generic 500 to avoid leaking
# internal details (e.g. BigQuery query strings) to the caller.
# ---------------------------------------------------------------------------
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "error": "Invalid request parameters",
            "detail": exc.errors(),
        },
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc),
        },
    )


# ---------------------------------------------------------------------------
# Routers
# Each router is responsible for one endpoint group.
# ---------------------------------------------------------------------------
app.include_router(schools.router)
app.include_router(recommend.router)
app.include_router(predict.router)


# ---------------------------------------------------------------------------
# Health check
# Intentionally kept in main.py — it has no business logic and no
# dependency on BigQuery. Cloud Run uses this for liveness checks.
# ---------------------------------------------------------------------------
@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok", "version": "0.1.0"}