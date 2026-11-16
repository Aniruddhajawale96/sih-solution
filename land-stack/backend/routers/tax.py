"""
routers/tax.py — Property-tax endpoints.

Routes
------
GET  /tax/{ulpin}  — All authenticated roles; returns TaxPublic for CITIZEN
                     (annual_tax omitted), TaxInternal for officers/admins.
PUT  /tax/{ulpin}  — TAX_OFF, STATE_ADMIN, NATL_ADMIN; updates the tax record,
                     writes audit REASSESS_TAX; returns TaxInternal.

All responses are wrapped in Envelope[T] via ok() / err().

Requirements: 8.1, 8.4
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.audit import write_audit
from core.database import get_db
from core.rbac import GLOBAL_ROLES, UserClaims, get_current_user, require_role
from core.response_schemas import TaxInternal, TaxPublic, TaxUpdate
from core.schemas import Envelope, ok
from models.tax import Tax

router = APIRouter()

# Roles permitted to mutate tax records (RBAC_MATRIX.md row 7)
_WRITE_ROLES = ["TAX_OFF", "STATE_ADMIN", "NATL_ADMIN"]


# ---------------------------------------------------------------------------
# GET /tax/{ulpin}  — read; CITIZEN gets TaxPublic, officers get TaxInternal
# ---------------------------------------------------------------------------


@router.get(
    "/{ulpin}",
    response_model=None,  # Union return: TaxPublic for CITIZEN, TaxInternal for officers
    summary="Get tax record for a parcel",
)
async def get_tax(
    ulpin: str,
    user: UserClaims = Depends(get_current_user),  # all authenticated roles
    db: AsyncSession = Depends(get_db),
) -> Envelope[TaxPublic] | Envelope[TaxInternal]:
    """
    Return the tax/assessment record for the given parcel.

    - CITIZEN callers receive ``TaxPublic`` (``annual_tax`` is omitted).
    - All officer and admin roles receive ``TaxInternal`` (all fields).
    """
    result = await db.execute(select(Tax).where(Tax.ulpin == ulpin))
    tax: Tax | None = result.scalar_one_or_none()

    if tax is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tax record for parcel {ulpin!r} not found",
        )

    if user.role == "CITIZEN":
        return ok(TaxPublic.model_validate(tax))

    return ok(TaxInternal.model_validate(tax))


# ---------------------------------------------------------------------------
# PUT /tax/{ulpin}  — officer write; audit + partial-update pattern
# ---------------------------------------------------------------------------


@router.put(
    "/{ulpin}",
    response_model=Envelope[TaxInternal],
    summary="Reassess / update tax record for a parcel",
)
async def update_tax(
    ulpin: str,
    body: TaxUpdate,
    user: UserClaims = Depends(require_role(_WRITE_ROLES)),
    db: AsyncSession = Depends(get_db),
) -> Envelope[TaxInternal]:
    """
    Update tax-assessment fields for the given parcel.

    - Only fields explicitly provided in the request body are modified
      (partial update via ``exclude_unset=True``).
    - Writes a ``REASSESS_TAX`` audit entry in the same DB transaction,
      before ``db.commit()``, per the audit-chain contract (design.md § 4).
    - Returns the updated record wrapped in ``Envelope[TaxInternal]``.
    """
    result = await db.execute(select(Tax).where(Tax.ulpin == ulpin))
    tax: Tax | None = result.scalar_one_or_none()

    if tax is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tax record for parcel {ulpin!r} not found",
        )

    # Apply only the fields supplied in the request body
    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(tax, field, value)

    # Write audit entry inside the same transaction (before commit)
    await write_audit(
        db=db,
        actor_user=user.username,
        actor_role=user.role,
        action="REASSESS_TAX",
        resource_type="tax",
        resource_id=ulpin,
    )

    await db.commit()
    await db.refresh(tax)

    return ok(TaxInternal.model_validate(tax))
