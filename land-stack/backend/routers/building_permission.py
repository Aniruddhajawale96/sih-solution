"""
routers/building_permission.py — Building Permission endpoints.

Routes
------
POST /building-permission          — create a building permission record;
                                     require PLAN_OFF, STATE_ADMIN, NATL_ADMIN;
                                     write audit CREATE_BUILDING_PERMISSION;
                                     return 201 BuildingPermissionInternal

GET  /building-permission/{ulpin}  — list all building permissions for a parcel;
                                     requires authentication (all roles);
                                     return list of BuildingPermissionPublic

Both BuildingPermissionPublic and BuildingPermissionInternal are identical
(public data — no masking required).
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
from core.response_schemas import (
    BuildingPermissionCreate,
    BuildingPermissionInternal,
    BuildingPermissionPublic,
)
from core.schemas import Envelope, err, ok
from models.building_permission import BuildingPermission
from models.parcel import Parcel

router = APIRouter()

# Roles permitted to create building permission records (RBAC_MATRIX.md)
_WRITE_ROLES = ["PLAN_OFF", "STATE_ADMIN", "NATL_ADMIN"]


# ---------------------------------------------------------------------------
# POST /building-permission — create a new building permission record
# ---------------------------------------------------------------------------


@router.post(
    "",
    response_model=Envelope[BuildingPermissionInternal],
    status_code=status.HTTP_201_CREATED,
    summary="Create a building permission record",
)
async def create_building_permission(
    body: BuildingPermissionCreate,
    user: UserClaims = Depends(require_role(_WRITE_ROLES)),
    db: AsyncSession = Depends(get_db),
) -> Envelope[BuildingPermissionInternal]:
    """
    Insert a new building permission row for the given ULPIN.

    - Requires role PLAN_OFF, STATE_ADMIN, or NATL_ADMIN.
    - Verifies the referenced parcel exists; returns 404 if not.
    - Writes an audit entry (CREATE_BUILDING_PERMISSION) in the same transaction.
    - Returns the created record as BuildingPermissionInternal (HTTP 201).
    """
    # Verify the referenced parcel exists
    parcel_result = await db.execute(
        select(Parcel.ulpin).where(Parcel.ulpin == body.ulpin)
    )
    if parcel_result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Parcel {body.ulpin!r} not found",
        )

    record = BuildingPermission(
        ulpin=body.ulpin,
        approval_no=body.approval_no,
        approved_built_up_area=body.approved_built_up_area,
        approval_date=body.approval_date,
        status=body.status,
        architect_ref=body.architect_ref,
    )
    db.add(record)
    await db.flush()  # populate record.id before audit write

    await write_audit(
        db=db,
        actor_user=user.username,
        actor_role=user.role,
        action="CREATE_BUILDING_PERMISSION",
        resource_type="building_permission",
        resource_id=str(record.id),
    )

    await db.commit()
    await db.refresh(record)

    return ok(BuildingPermissionInternal.model_validate(record))


# ---------------------------------------------------------------------------
# GET /building-permission/{ulpin} — list building permissions for a parcel
# ---------------------------------------------------------------------------


@router.get(
    "/{ulpin}",
    response_model=Envelope[List[BuildingPermissionPublic]],
    status_code=status.HTTP_200_OK,
    summary="List building permissions for a parcel",
)
async def list_building_permissions(
    ulpin: str,
    _user: UserClaims = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Envelope[List[BuildingPermissionPublic]]:
    """
    Return all building permission records for the given ULPIN.

    - Requires any authenticated role (all 7 roles).
    - No field masking — building permission data is fully public.
    - Returns HTTP 404 if the parcel does not exist.
    """
    # Verify the parcel exists
    parcel_result = await db.execute(
        select(Parcel.ulpin).where(Parcel.ulpin == ulpin)
    )
    if parcel_result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Parcel {ulpin!r} not found",
        )

    rows_result = await db.execute(
        select(BuildingPermission)
        .where(BuildingPermission.ulpin == ulpin)
        .order_by(BuildingPermission.id)
    )
    records = rows_result.scalars().all()

    return ok([BuildingPermissionPublic.model_validate(r) for r in records])
