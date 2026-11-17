"""
routers/registration.py — Deed registration endpoints.

POST /registration        — REG_OFF, STATE_ADMIN, NATL_ADMIN; insert Registration;
                            write audit REGISTER_DEED; publish registration.completed
                            to Redis; return 201 RegistrationInternal
GET  /registration        — all authenticated roles; list with optional ?ulpin= filter;
                            CITIZEN/REV_OFF receive RegistrationPublic (transaction_value
                            omitted, buyer/seller masked); others receive RegistrationInternal
GET  /registration/{id}   — single record with the same masking logic

Requirements: 8.1, 8.4
"""

from __future__ import annotations

import json

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.audit import write_audit
from core.database import get_db
from core.rbac import UserClaims, check_jurisdiction, get_current_user, require_role
from core.redis_client import get_redis
from core.response_schemas import (
    RegistrationCreate,
    RegistrationInternal,
    RegistrationPublic,
    mask_name,
)
from core.schemas import Envelope, err, ok
from models.registration import Registration

router = APIRouter()

# ---------------------------------------------------------------------------
# Role sets
# ---------------------------------------------------------------------------

# Roles allowed to create registrations
_WRITE_ROLES = ["REG_OFF", "STATE_ADMIN", "NATL_ADMIN"]

# Roles that receive the full internal view (transaction_value included, names unmasked)
_INTERNAL_ROLES = {"REG_OFF", "STATE_ADMIN", "NATL_ADMIN"}

# Roles that use the public (masked) view
_PUBLIC_ROLES = {"CITIZEN", "REV_OFF"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _to_public(reg: Registration) -> RegistrationPublic:
    """Serialise a Registration ORM row as RegistrationPublic (masked)."""
    return RegistrationPublic(
        id=reg.id,
        ulpin=reg.ulpin,
        deed_no=reg.deed_no,
        deed_type=reg.deed_type,
        registration_date=reg.registration_date,
        sro_office=reg.sro_office,
        buyer=mask_name(reg.buyer),
        seller=mask_name(reg.seller),
        stamp_duty_paid=reg.stamp_duty_paid,
    )


def _to_internal(reg: Registration) -> RegistrationInternal:
    """Serialise a Registration ORM row as RegistrationInternal (all fields)."""
    return RegistrationInternal(
        id=reg.id,
        ulpin=reg.ulpin,
        deed_no=reg.deed_no,
        deed_type=reg.deed_type,
        registration_date=reg.registration_date,
        sro_office=reg.sro_office,
        buyer=reg.buyer,
        seller=reg.seller,
        stamp_duty_paid=reg.stamp_duty_paid,
        transaction_value=reg.transaction_value,
    )


def _serialise(reg: Registration, user: UserClaims) -> RegistrationPublic | RegistrationInternal:
    """Choose public or internal serialisation based on the caller's role."""
    if user.role in _INTERNAL_ROLES:
        return _to_internal(reg)
    return _to_public(reg)


# ---------------------------------------------------------------------------
# POST /registration
# ---------------------------------------------------------------------------

@router.post(
    "",
    response_model=Envelope[RegistrationInternal],
    status_code=status.HTTP_201_CREATED,
    summary="Register a deed",
)
async def create_registration(
    body: RegistrationCreate,
    user: UserClaims = Depends(require_role(_WRITE_ROLES)),
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
) -> Envelope[RegistrationInternal]:
    """
    Insert a new Registration row for the given ULPIN.

    - Writes an audit entry (REGISTER_DEED) inside the same transaction.
    - Commits both the registration row and the audit entry atomically.
    - Publishes `registration.completed` to Redis after the commit so the
      Workflow Engine consumer can create a MUTATION task.
    - Returns the full RegistrationInternal payload (transaction_value visible).
    """
    reg = Registration(
        ulpin=body.ulpin,
        deed_no=body.deed_no,
        deed_type=body.deed_type,
        registration_date=body.registration_date,
        sro_office=body.sro_office,
        buyer=body.buyer,
        seller=body.seller,
        transaction_value=body.transaction_value,
        stamp_duty_paid=body.stamp_duty_paid,
    )
    db.add(reg)
    # Flush to obtain the auto-incremented `id` before the audit write so we can
    # record the resource_id correctly without committing yet.
    await db.flush()

    await write_audit(
        db=db,
        actor_user=user.username,
        actor_role=user.role,
        action="REGISTER_DEED",
        resource_type="registration",
        resource_id=str(reg.id),
    )

    await db.commit()
    await db.refresh(reg)

    # Publish event to Redis for the Workflow Engine consumer (best-effort; do
    # not let a Redis failure roll back the already-committed transaction).
    event_payload = json.dumps(
        {
            "ulpin": reg.ulpin,
            "deed_no": reg.deed_no,
            "registration_id": reg.id,
        }
    )
    try:
        await redis.publish("registration.completed", event_payload)
    except Exception:
        # Non-fatal: the commit already succeeded; log in production.
        pass

    return ok(_to_internal(reg))


# ---------------------------------------------------------------------------
# GET /registration
# ---------------------------------------------------------------------------

@router.get(
    "",
    response_model=Envelope[list[RegistrationPublic | RegistrationInternal]],
    status_code=status.HTTP_200_OK,
    summary="List registrations",
)
async def list_registrations(
    ulpin: str | None = Query(default=None, description="Filter by ULPIN"),
    limit: int = Query(default=50, ge=1, le=500, description="Max rows to return"),
    offset: int = Query(default=0, ge=0, description="Rows to skip"),
    user: UserClaims = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Envelope[list]:
    """
    Return a paginated list of Registration records.

    - Optional `?ulpin=<ULPIN>` filter narrows results to one parcel.
    - CITIZEN and REV_OFF receive RegistrationPublic (transaction_value omitted,
      buyer/seller name-masked).
    - REG_OFF, STATE_ADMIN, NATL_ADMIN receive RegistrationInternal (all fields).
    """
    stmt = select(Registration)
    if ulpin is not None:
        stmt = stmt.where(Registration.ulpin == ulpin)
    stmt = stmt.order_by(Registration.id).offset(offset).limit(limit)

    result = await db.execute(stmt)
    rows: list[Registration] = list(result.scalars().all())

    return ok([_serialise(r, user) for r in rows])


# ---------------------------------------------------------------------------
# GET /registration/{id}
# ---------------------------------------------------------------------------

@router.get(
    "/{registration_id}",
    response_model=Envelope[RegistrationPublic | RegistrationInternal],
    status_code=status.HTTP_200_OK,
    summary="Get a single registration",
)
async def get_registration(
    registration_id: int,
    user: UserClaims = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Envelope:
    """
    Fetch a single Registration by its integer id.

    Returns 404 if the record does not exist.
    Applies the same Public/Internal masking as the list endpoint.
    """
    reg: Registration | None = await db.get(Registration, registration_id)
    if reg is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Registration {registration_id} not found",
        )

    return ok(_serialise(reg, user))
