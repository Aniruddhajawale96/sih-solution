"""
routers/encumbrance.py — Encumbrance endpoints.

POST /encumbrance        — create an encumbrance record; require REG_OFF, STATE_ADMIN, NATL_ADMIN
GET  /encumbrance/{ulpin} — list all encumbrances for a parcel; requires authentication (all roles)

Both public and internal views are identical (no masking — public transparency requirement).
All responses are wrapped in Envelope[T] using ok() / err() helpers.
Requirements: 8.1, 8.4
"""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.audit import write_audit
from core.database import get_db
from core.rbac import UserClaims, get_current_user, require_role
from core.schemas import Envelope, err, ok
from core.response_schemas import EncumbranceCreate, EncumbranceInternal, EncumbrancePublic
from models.encumbrance import Encumbrance
from models.parcel import Parcel

router = APIRouter()


# ---------------------------------------------------------------------------
# POST /encumbrance — create a new encumbrance record
# ---------------------------------------------------------------------------

@router.post(
    "",
    response_model=Envelope[EncumbranceInternal],
    status_code=status.HTTP_201_CREATED,
    summary="Create an encumbrance record",
)
async def create_encumbrance(
    body: EncumbranceCreate,
    user: UserClaims = Depends(require_role(["REG_OFF", "STATE_ADMIN", "NATL_ADMIN"])),
    db: AsyncSession = Depends(get_db),
) -> Envelope[EncumbranceInternal]:
    """
    Insert a new encumbrance row for the given ULPIN.

    - Requires role REG_OFF, STATE_ADMIN, or NATL_ADMIN.
    - Writes an audit entry (CREATE_ENCUMBRANCE) in the same transaction.
    - Returns the created record as EncumbranceInternal (HTTP 201).
    """
    # Verify the referenced parcel exists
    result = await db.execute(select(Parcel.ulpin).where(Parcel.ulpin == body.ulpin))
    if result.scalar_one_or_none() is None:
        return err(code="NOT_FOUND", message=f"Parcel {body.ulpin!r} not found")

    record = Encumbrance(
        ulpin=body.ulpin,
        type=body.type,
        institution=body.institution,
        status=body.status,
        date=body.date,
    )
    db.add(record)
    await db.flush()  # populate record.id before audit write

    await write_audit(
        db=db,
        actor_user=user.username,
        actor_role=user.role,
        action="CREATE_ENCUMBRANCE",
        resource_type="encumbrance",
        resource_id=str(record.id),
    )

    await db.commit()
    await db.refresh(record)

    return ok(EncumbranceInternal.model_validate(record))


# ---------------------------------------------------------------------------
# GET /encumbrance/{ulpin} — list encumbrances for a parcel
# ---------------------------------------------------------------------------

@router.get(
    "/{ulpin}",
    response_model=Envelope[List[EncumbrancePublic]],
    status_code=status.HTTP_200_OK,
    summary="List encumbrances for a parcel",
)
async def list_encumbrances(
    ulpin: str,
    user: UserClaims = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Envelope[List[EncumbrancePublic]]:
    """
    Return all encumbrance records for the given ULPIN.

    - Requires any authenticated role (all 7 roles).
    - No field masking — encumbrance data is fully public per transparency rules.
    - Returns HTTP 404 if the parcel does not exist.
    """
    # Verify the parcel exists
    parcel_result = await db.execute(select(Parcel.ulpin).where(Parcel.ulpin == ulpin))
    if parcel_result.scalar_one_or_none() is None:
        return err(code="NOT_FOUND", message=f"Parcel {ulpin!r} not found")

    rows_result = await db.execute(
        select(Encumbrance).where(Encumbrance.ulpin == ulpin).order_by(Encumbrance.id)
    )
    records = rows_result.scalars().all()

    return ok([EncumbrancePublic.model_validate(r) for r in records])
