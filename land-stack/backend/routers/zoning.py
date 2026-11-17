"""
routers/zoning.py — Zoning / Master-Plan endpoints.

Routes
------
GET  /zoning/{ulpin}   — Public (all authenticated roles); returns ZoningPublic
PUT  /zoning/{ulpin}   — PLAN_OFF, STATE_ADMIN, NATL_ADMIN; updates zoning record,
                         auto-sets violation_flag, writes audit UPDATE_ZONING;
                         returns ZoningInternal

Both ZoningPublic and ZoningInternal are identical (FAR data is fully public).
All responses are wrapped in Envelope[T] via ok() / err().

Requirements: 8.1, 8.4
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.audit import write_audit
from core.database import get_db
from core.rbac import UserClaims, get_current_user, require_role
from core.response_schemas import ZoningInternal, ZoningPublic, ZoningUpdate
from core.schemas import Envelope, err, ok
from models.zoning import Zoning

router = APIRouter()

# Roles permitted to mutate zoning records (RBAC_MATRIX.md)
_WRITE_ROLES = ["PLAN_OFF", "STATE_ADMIN", "NATL_ADMIN"]


# ---------------------------------------------------------------------------
# GET /zoning/{ulpin}  — public read (all authenticated roles)
# ---------------------------------------------------------------------------


@router.get(
    "/{ulpin}",
    response_model=Envelope[ZoningPublic],
    summary="Get zoning record for a parcel",
)
async def get_zoning(
    ulpin: str,
    _user: UserClaims = Depends(get_current_user),  # any authenticated caller
    db: AsyncSession = Depends(get_db),
) -> Envelope[ZoningPublic]:
    """Return the zoning / master-plan record for the given parcel."""
    result = await db.execute(select(Zoning).where(Zoning.ulpin == ulpin))
    zoning: Zoning | None = result.scalar_one_or_none()

    if zoning is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Zoning record for parcel {ulpin!r} not found",
        )

    return ok(ZoningPublic.model_validate(zoning))


# ---------------------------------------------------------------------------
# PUT /zoning/{ulpin}  — officer write; audit + violation_flag auto-set
# ---------------------------------------------------------------------------


@router.put(
    "/{ulpin}",
    response_model=Envelope[ZoningInternal],
    summary="Update zoning record for a parcel",
)
async def update_zoning(
    ulpin: str,
    body: ZoningUpdate,
    user: UserClaims = Depends(require_role(_WRITE_ROLES)),
    db: AsyncSession = Depends(get_db),
) -> Envelope[ZoningInternal]:
    """
    Update zoning fields for the given parcel.

    - ``violation_flag`` is computed automatically:
      ``True`` when ``far_existing > far_permitted`` after the update.
    - Writes an ``UPDATE_ZONING`` audit entry in the same transaction.
    - Returns the updated record wrapped in ``Envelope[ZoningInternal]``.
    """
    result = await db.execute(select(Zoning).where(Zoning.ulpin == ulpin))
    zoning: Zoning | None = result.scalar_one_or_none()

    if zoning is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Zoning record for parcel {ulpin!r} not found",
        )

    # Apply partial updates — only fields explicitly provided in the request body
    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(zoning, field, value)

    # Recompute violation_flag from current far values after any update
    zoning.violation_flag = zoning.far_existing > zoning.far_permitted

    # Write audit entry inside the same transaction (before commit)
    await write_audit(
        db=db,
        actor_user=user.username,
        actor_role=user.role,
        action="UPDATE_ZONING",
        resource_type="zoning",
        resource_id=ulpin,
    )

    await db.commit()
    await db.refresh(zoning)

    return ok(ZoningInternal.model_validate(zoning))
