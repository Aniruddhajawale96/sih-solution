"""
main.py — Land Stack FastAPI application entry point.

Responsibilities
----------------
- Instantiate the FastAPI app with metadata.
- Register a lifespan context that starts the workflow-engine consumer task
  and cancels it cleanly on shutdown.
- Add global exception handlers for 404, 422, and 500 errors that return a
  consistent Envelope response (never raw FastAPI defaults).
- Mount every domain router under the /api/v1 prefix.
"""

from __future__ import annotations
from dotenv import load_dotenv
load_dotenv()

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from core.schemas import err
from workflow_engine.consumer import start_consumer

# Domain routers ----------------------------------------------------------------
from routers import auth as auth_router
from routers import parcel as parcel_router
from routers import ror as ror_router
from routers import registration as registration_router
from routers import encumbrance as encumbrance_router
from routers import zoning as zoning_router
from routers import building_permission as building_permission_router
from routers import tax as tax_router
from routers import workflow as workflow_router
from routers import citizen as citizen_router
from routers import admin as admin_router
from routers import analytics as analytics_router
from routers import ml as ml_router

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Start background tasks on startup; cancel them on shutdown."""
    consumer_task = asyncio.create_task(start_consumer(), name="workflow-consumer")
    logger.info("Workflow engine consumer task created.")

    try:
        yield
    finally:
        if not consumer_task.done():
            consumer_task.cancel()
            try:
                await consumer_task
            except asyncio.CancelledError:
                pass
        logger.info("Workflow engine consumer task stopped.")


# ---------------------------------------------------------------------------
# Application instance
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Land Stack API",
    version="1.0.0",
    description=(
        "Unified land-records platform for India (SIH PS #26014). "
        "All responses follow the Envelope[T] schema."
    ),
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Global exception handlers
# ---------------------------------------------------------------------------

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Return Envelope-formatted JSON for all HTTP errors (404, 403, etc.)."""
    code_map = {
        404: "NOT_FOUND",
        403: "FORBIDDEN",
        401: "UNAUTHORIZED",
        405: "METHOD_NOT_ALLOWED",
    }
    code = code_map.get(exc.status_code, f"HTTP_{exc.status_code}")
    envelope = err(code=code, message=str(exc.detail))
    return JSONResponse(
        status_code=exc.status_code,
        content=envelope.model_dump(),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Return Envelope-formatted JSON for Pydantic/FastAPI 422 validation errors."""
    # Collect the first validation error as the primary message; include field path.
    first = exc.errors()[0] if exc.errors() else {}
    field = ".".join(str(loc) for loc in first.get("loc", [])) or None
    message = first.get("msg", "Validation error")
    envelope = err(code="VALIDATION_ERROR", message=message, field=field)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=envelope.model_dump(),
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all handler that returns Envelope for unexpected 500 errors."""
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    envelope = err(code="INTERNAL_SERVER_ERROR", message="An unexpected error occurred.")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=envelope.model_dump(),
    )


# ---------------------------------------------------------------------------
# Router registration
# ---------------------------------------------------------------------------

_API_PREFIX = "/api/v1"

app.include_router(auth_router.router,                prefix=f"{_API_PREFIX}/auth",               tags=["Auth"])
app.include_router(parcel_router.router,              prefix=f"{_API_PREFIX}/parcels",             tags=["Parcels"])
app.include_router(ror_router.router,                 prefix=f"{_API_PREFIX}/ror",                 tags=["RoR"])
app.include_router(registration_router.router,        prefix=f"{_API_PREFIX}/registration",        tags=["Registration"])
app.include_router(encumbrance_router.router,         prefix=f"{_API_PREFIX}/encumbrance",         tags=["Encumbrance"])
app.include_router(zoning_router.router,              prefix=f"{_API_PREFIX}/zoning",              tags=["Zoning"])
app.include_router(building_permission_router.router, prefix=f"{_API_PREFIX}/building-permission", tags=["BuildingPermission"])
app.include_router(tax_router.router,                 prefix=f"{_API_PREFIX}/tax",                 tags=["Tax"])
app.include_router(workflow_router.router,            prefix=f"{_API_PREFIX}/workflow",            tags=["Workflow"])
app.include_router(citizen_router.router,             prefix=f"{_API_PREFIX}/citizen",             tags=["Citizen"])
app.include_router(admin_router.router,               prefix=f"{_API_PREFIX}/admin",               tags=["Admin"])
app.include_router(analytics_router.router,           prefix=f"{_API_PREFIX}/analytics",           tags=["Analytics"])
app.include_router(ml_router.router,                  prefix=f"{_API_PREFIX}/ml",                  tags=["ML"])
