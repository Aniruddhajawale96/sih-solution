"""
routers/citizen.py — Citizen self-service endpoints.

Routes
------
POST /citizen/service-request
    Require CITIZEN role; insert CitizenServiceRequest; write audit
    CITIZEN_SERVICE_REQUEST; return 201 {request_id, status}.

GET  /citizen/requests
    Require CITIZEN role; return service requests scoped to the calling
    citizen's username (current_user.username).

GET  /citizen/parcels
    Require CITIZEN role; query ror.owner_name ILIKE %citizen_name% (using
    current_user.username as the search term) and join with parcels; return
    list of ParcelPublic.

Requirements: 8.1, 8.4
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.audit import write_audit
from core.database import get_db
from core.rbac import UserClaims, require_role
from core.response_schemas import (
    CitizenServiceRequestCreate,
    CitizenServiceRequestResponse,
    CitizenServiceRequestSubmitted,
    ParcelPublic,
)
from core.schemas import Envelope, ok
from models.parcel import Parcel
from models.ror import Ror
from models.workflow import CitizenServiceRequest

router = APIRouter()

_CITIZEN = ["CITIZEN"]


# ---------------------------------------------------------------------------
# POST /citizen/service-request
# ---------------------------------------------------------------------------


@router.post(
    "/service-request",
    response_model=Envelope[CitizenServiceRequestSubmitted],
    status_code=status.HTTP_201_CREATED,
    summary="Submit a citizen service request",
)
async def create_service_request(
    body: CitizenServiceRequestCreate,
    user: UserClaims = Depends(require_role(_CITIZEN)),
    db: AsyncSession = Depends(get_db),
) -> Envelope[CitizenServiceRequestSubmitted]:
    """
    Insert a new CitizenServiceRequest row and write an audit entry.

    - Only CITIZEN role may call this endpoint.
    - Generates a UUID for the new request.
    - Writes audit action ``CITIZEN_SERVICE_REQUEST`` inside the same transaction.
    - Commits both the service request row and the audit entry atomically.
    - Returns minimal confirmation: ``{request_id, status}``.
    """
    request_id = str(uuid.uuid4())

    service_request = CitizenServiceRequest(
        id=request_id,
        ulpin=body.ulpin,
        citizen_username=user.username,
        service_type=body.service_type,
        notes=body.notes,
        status="submitted",
    )
    db.add(service_request)
    await db.flush()  # populate id without committing so audit can reference it

    await write_audit(
        db=db,
        actor_user=user.username,
        actor_role=user.role,
        action="CITIZEN_SERVICE_REQUEST",
        resource_type="citizen_service_request",
        resource_id=request_id,
    )

    await db.commit()

    return ok(CitizenServiceRequestSubmitted(request_id=request_id, status="submitted"))


# ---------------------------------------------------------------------------
# GET /citizen/requests
# ---------------------------------------------------------------------------


@router.get(
    "/requests",
    response_model=Envelope[list[CitizenServiceRequestResponse]],
    status_code=status.HTTP_200_OK,
    summary="List the calling citizen's service requests",
)
async def list_citizen_requests(
    status_filter: Annotated[
        str | None,
        Query(
            alias="status",
            description="Filter by request status (submitted/approved/rejected)",
        ),
    ] = None,
    user: UserClaims = Depends(require_role(_CITIZEN)),
    db: AsyncSession = Depends(get_db),
) -> Envelope[list[CitizenServiceRequestResponse]]:
    """
    Return all service requests submitted by the calling citizen.

    Results are scoped strictly to ``current_user.username`` — a citizen cannot
    see another citizen's requests. An optional ``?status=`` query param narrows
    results to a single status value.
    """
    stmt = (
        select(CitizenServiceRequest)
        .where(CitizenServiceRequest.citizen_username == user.username)
    )
    if status_filter is not None:
        stmt = stmt.where(CitizenServiceRequest.status == status_filter)
    stmt = stmt.order_by(CitizenServiceRequest.created_at.desc())

    result = await db.execute(stmt)
    rows = list(result.scalars().all())

    return ok([CitizenServiceRequestResponse.model_validate(r) for r in rows])


# ---------------------------------------------------------------------------
# GET /citizen/parcels
# ---------------------------------------------------------------------------


@router.get(
    "/parcels",
    response_model=Envelope[list[ParcelPublic]],
    status_code=status.HTTP_200_OK,
    summary="Parcels owned by the calling citizen (by name match)",
)
async def get_citizen_parcels(
    user: UserClaims = Depends(require_role(_CITIZEN)),
    db: AsyncSession = Depends(get_db),
) -> Envelope[list[ParcelPublic]]:
    """
    Return parcels whose RoR ``owner_name`` matches the citizen's username.

    Uses a case-insensitive ILIKE ``%<username>%`` pattern so the match is
    partial and accent-insensitive on PostgreSQL. The RoR row is joined with
    the parcels table and results are returned as ``ParcelPublic`` (no geometry).
    """
    pattern = f"%{user.username}%"

    result = await db.execute(
        select(Parcel)
        .join(Ror, Ror.ulpin == Parcel.ulpin)
        .where(Ror.owner_name.ilike(pattern))
        .order_by(Parcel.ulpin)
    )
    rows = list(result.scalars().all())

    return ok([ParcelPublic.model_validate(r) for r in rows])
