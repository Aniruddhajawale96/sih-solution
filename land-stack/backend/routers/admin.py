"""
routers/admin.py — Admin endpoints for state adapter configuration and user management.

Endpoints
---------
GET  /admin/state-adapter/{state_code}
    STATE_ADMIN (own state only) or NATL_ADMIN.
    Returns the full list of StateAdapterConfig rows for the given state.

PUT  /admin/state-adapter/{state_code}
    NATL_ADMIN only.
    Partially updates all matching StateAdapterConfig rows for the state.
    Writes audit UPDATE_STATE_ADAPTER inside the same transaction.

GET  /admin/users
    STATE_ADMIN (users whose jurisdiction matches caller's) or NATL_ADMIN (all users).
    Returns UserInternal list (hashed_password never exposed).

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
from core.response_schemas import (
    StateAdapterConfig as StateAdapterConfigSchema,
    StateAdapterConfigUpdate,
    UserInternal,
)
from core.schemas import Envelope, ok
from models.state_adapter import StateAdapterConfig
from models.users import User

router = APIRouter()

# Roles permitted to read state adapter configs or user lists
_READ_ROLES = ["STATE_ADMIN", "NATL_ADMIN"]

# Only NATL_ADMIN may mutate state adapter configs
_WRITE_ROLES = ["NATL_ADMIN"]


# ---------------------------------------------------------------------------
# GET /admin/state-adapter/{state_code}
# ---------------------------------------------------------------------------


@router.get(
    "/state-adapter/{state_code}",
    response_model=Envelope[list[StateAdapterConfigSchema]],
    summary="Get state adapter config for a state",
)
async def get_state_adapter(
    state_code: str,
    user: UserClaims = Depends(require_role(_READ_ROLES)),
    db: AsyncSession = Depends(get_db),
) -> Envelope[list[StateAdapterConfigSchema]]:
    """
    Return all adapter config rows for the given state.

    - ``STATE_ADMIN`` may only retrieve config for their own jurisdiction
      (``user.jurisdiction`` must match ``state_code``).
    - ``NATL_ADMIN`` may retrieve config for any state.
    """
    if user.role == "STATE_ADMIN" and user.jurisdiction != state_code:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"STATE_ADMIN jurisdiction {user.jurisdiction!r} does not match "
                f"requested state {state_code!r}"
            ),
        )

    result = await db.execute(
        select(StateAdapterConfig).where(StateAdapterConfig.state_code == state_code)
    )
    configs: list[StateAdapterConfig] = list(result.scalars().all())

    return ok([StateAdapterConfigSchema.model_validate(c) for c in configs])


# ---------------------------------------------------------------------------
# PUT /admin/state-adapter/{state_code}
# ---------------------------------------------------------------------------


@router.put(
    "/state-adapter/{state_code}",
    response_model=Envelope[list[StateAdapterConfigSchema]],
    summary="Update state adapter config for a state (NATL_ADMIN only)",
)
async def update_state_adapter(
    state_code: str,
    body: StateAdapterConfigUpdate,
    user: UserClaims = Depends(require_role(_WRITE_ROLES)),
    db: AsyncSession = Depends(get_db),
) -> Envelope[list[StateAdapterConfigSchema]]:
    """
    Partially update all StateAdapterConfig rows for a given state.

    Only fields explicitly provided in the request body are modified
    (partial update via ``exclude_unset=True``).

    Writes a single ``UPDATE_STATE_ADAPTER`` audit entry in the same DB
    transaction (before ``db.commit()``), per the audit-chain contract.

    Returns the full updated config list for the state.
    """
    result = await db.execute(
        select(StateAdapterConfig).where(StateAdapterConfig.state_code == state_code)
    )
    configs: list[StateAdapterConfig] = list(result.scalars().all())

    if not configs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No adapter config rows found for state {state_code!r}",
        )

    update_data = body.model_dump(exclude_unset=True)
    for config in configs:
        for field, value in update_data.items():
            setattr(config, field, value)

    # Write a single audit entry for the entire state's config update.
    await write_audit(
        db=db,
        actor_user=user.username,
        actor_role=user.role,
        action="UPDATE_STATE_ADAPTER",
        resource_type="state_adapter_config",
        resource_id=state_code,
    )

    await db.commit()

    # Refresh all updated rows.
    for config in configs:
        await db.refresh(config)

    return ok([StateAdapterConfigSchema.model_validate(c) for c in configs])


# ---------------------------------------------------------------------------
# GET /admin/users
# ---------------------------------------------------------------------------


@router.get(
    "/users",
    response_model=Envelope[list[UserInternal]],
    summary="List users (STATE_ADMIN sees own jurisdiction; NATL_ADMIN sees all)",
)
async def list_users(
    user: UserClaims = Depends(require_role(_READ_ROLES)),
    db: AsyncSession = Depends(get_db),
) -> Envelope[list[UserInternal]]:
    """
    Return a list of User records with ``hashed_password`` never included.

    - ``STATE_ADMIN`` receives only users whose ``jurisdiction`` matches the
      caller's own ``jurisdiction``.
    - ``NATL_ADMIN`` receives all users across all jurisdictions.
    """
    stmt = select(User)

    if user.role == "STATE_ADMIN":
        stmt = stmt.where(User.jurisdiction == user.jurisdiction)

    result = await db.execute(stmt)
    users: list[User] = list(result.scalars().all())

    return ok([UserInternal.model_validate(u) for u in users])
