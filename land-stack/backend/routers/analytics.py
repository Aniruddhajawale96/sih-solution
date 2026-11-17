"""
routers/analytics.py — Analytics endpoints.

Endpoints
---------
GET  /analytics/national
    NATL_ADMIN only.
    Returns national aggregate statistics across all states.

GET  /analytics/state/{state_code}
    STATE_ADMIN (own state only) or NATL_ADMIN.
    Returns per-state aggregate statistics.
    STATE_ADMIN requesting a mismatched state_code → 403.

GET  /analytics/audit/{ulpin}
    All authenticated roles.
    CITIZEN → AuditLogPublic list (actor_user, hash, prev_hash omitted).
    Officers → AuditLogInternal list (full chain).
    Filtered by resource_id == ulpin, ordered by id ASC.

No write operations in this router → no audit writes needed.

Requirements: 8.1, 8.4
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.rbac import GLOBAL_ROLES, UserClaims, get_current_user, require_role
from core.response_schemas import AuditLogInternal, AuditLogPublic, NationalAnalytics, StateAnalytics
from core.schemas import Envelope, ok
from models.audit_log import AuditLog
from models.parcel import Parcel
from models.tax import Tax
from models.workflow import WorkflowTask
from models.zoning import Zoning

router = APIRouter()

# ---------------------------------------------------------------------------
# Role lists
# ---------------------------------------------------------------------------

_NATL_ADMIN_ONLY = ["NATL_ADMIN"]
_STATE_OR_NATL = ["STATE_ADMIN", "NATL_ADMIN"]

# All 7 roles — any authenticated caller may read the audit chain.
_ALL_ROLES = ["CITIZEN", "REV_OFF", "REG_OFF", "PLAN_OFF", "TAX_OFF", "STATE_ADMIN", "NATL_ADMIN"]


# ---------------------------------------------------------------------------
# GET /analytics/national
# ---------------------------------------------------------------------------


@router.get(
    "/national",
    response_model=Envelope[NationalAnalytics],
    summary="National aggregate statistics (NATL_ADMIN only)",
)
async def get_national_analytics(
    user: UserClaims = Depends(require_role(_NATL_ADMIN_ONLY)),
    db: AsyncSession = Depends(get_db),
) -> Envelope[NationalAnalytics]:
    """
    Return national aggregate dashboard data:

    - Total parcel count across all states.
    - Parcel count grouped by state_code.
    - Number of zoning rows where violation_flag is True.
    - Number of workflow_tasks rows where status == 'pending'.
    - Number of registrations where fraud_flagged is True  (skipped — field absent → 0).
    """
    # Total parcel count
    result = await db.execute(select(func.count()).select_from(Parcel))
    parcels_total: int = result.scalar_one()

    # Parcel count per state
    result = await db.execute(
        select(Parcel.state_code, func.count().label("cnt"))
        .group_by(Parcel.state_code)
    )
    by_state: dict[str, int] = {row.state_code: row.cnt for row in result.all()}

    # Zoning violations
    result = await db.execute(
        select(func.count()).select_from(Zoning).where(Zoning.violation_flag.is_(True))
    )
    violations: int = result.scalar_one()

    # Pending workflow tasks
    result = await db.execute(
        select(func.count())
        .select_from(WorkflowTask)
        .where(WorkflowTask.status == "pending")
    )
    pending_mutations: int = result.scalar_one()

    # fraud_flagged is not present on the Registration model — return 0.
    fraud_flags: int = 0

    return ok(
        NationalAnalytics(
            parcels_total=parcels_total,
            by_state=by_state,
            violations=violations,
            pending_mutations=pending_mutations,
            fraud_flags=fraud_flags,
        )
    )


# ---------------------------------------------------------------------------
# GET /analytics/state/{state_code}
# ---------------------------------------------------------------------------


@router.get(
    "/state/{state_code}",
    response_model=Envelope[StateAnalytics],
    summary="State-level aggregate statistics (STATE_ADMIN own state or NATL_ADMIN)",
)
async def get_state_analytics(
    state_code: str,
    user: UserClaims = Depends(require_role(_STATE_OR_NATL)),
    db: AsyncSession = Depends(get_db),
) -> Envelope[StateAnalytics]:
    """
    Return aggregate dashboard data scoped to *state_code*.

    - ``STATE_ADMIN`` may only query their own jurisdiction; a mismatch → 403.
    - ``NATL_ADMIN`` may query any state.

    Aggregates (all scoped via JOIN to parcels.state_code):
    - Total parcel count in the state.
    - Zoning violations within the state.
    - Pending workflow_tasks within the state.
    - Sum of tax.arrears across the state.
    """
    if user.role == "STATE_ADMIN" and user.jurisdiction != state_code:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"STATE_ADMIN jurisdiction {user.jurisdiction!r} does not match "
                f"requested state {state_code!r}"
            ),
        )

    # Parcels total for this state
    result = await db.execute(
        select(func.count()).select_from(Parcel).where(Parcel.state_code == state_code)
    )
    parcels_total: int = result.scalar_one()

    # Zoning violations: JOIN zoning → parcels on ulpin, filter by state_code
    result = await db.execute(
        select(func.count())
        .select_from(Zoning)
        .join(Parcel, Zoning.ulpin == Parcel.ulpin)
        .where(Parcel.state_code == state_code)
        .where(Zoning.violation_flag.is_(True))
    )
    violations: int = result.scalar_one()

    # Pending workflow tasks: JOIN workflow_tasks → parcels on ulpin
    result = await db.execute(
        select(func.count())
        .select_from(WorkflowTask)
        .join(Parcel, WorkflowTask.ulpin == Parcel.ulpin)
        .where(Parcel.state_code == state_code)
        .where(WorkflowTask.status == "pending")
    )
    pending_mutations: int = result.scalar_one()

    # Sum of tax arrears: JOIN tax → parcels on ulpin
    result = await db.execute(
        select(func.coalesce(func.sum(Tax.arrears), 0))
        .select_from(Tax)
        .join(Parcel, Tax.ulpin == Parcel.ulpin)
        .where(Parcel.state_code == state_code)
    )
    arrears_total: int = result.scalar_one()

    return ok(
        StateAnalytics(
            parcels_total=parcels_total,
            violations=violations,
            pending_mutations=pending_mutations,
            arrears_total=arrears_total,
        )
    )


# ---------------------------------------------------------------------------
# GET /analytics/audit/{ulpin}
# ---------------------------------------------------------------------------


@router.get(
    "/audit/{ulpin}",
    response_model=Envelope[list[AuditLogPublic] | list[AuditLogInternal]],
    summary="Hash-chained audit trail for a parcel (all authenticated roles)",
)
async def get_audit_chain(
    ulpin: str,
    user: UserClaims = Depends(require_role(_ALL_ROLES)),
    db: AsyncSession = Depends(get_db),
) -> Envelope[list[AuditLogPublic] | list[AuditLogInternal]]:
    """
    Return the audit log chain for the given ULPIN, ordered by id ascending
    (chain order).

    - CITIZEN callers receive ``AuditLogPublic`` (actor_user, hash, prev_hash omitted).
    - Any officer or admin role receives ``AuditLogInternal`` (full chain fields).

    The filter is ``resource_id == ulpin``; this is the join key across the platform.
    """
    result = await db.execute(
        select(AuditLog)
        .where(AuditLog.resource_id == ulpin)
        .order_by(AuditLog.id.asc())
    )
    rows: list[AuditLog] = list(result.scalars().all())

    if user.role == "CITIZEN":
        entries: list[AuditLogPublic] | list[AuditLogInternal] = [
            AuditLogPublic.model_validate(row) for row in rows
        ]
    else:
        entries = [AuditLogInternal.model_validate(row) for row in rows]

    return ok(entries)
