"""
routers/ror.py — Record of Rights (RoR) endpoints.

Routes
------
GET  /ror/{ulpin}   Return RorPublic (CITIZEN) or RorInternal (officer/admin).
                    Accessible to all authenticated roles.

PUT  /ror/{ulpin}   Update RoR fields; requires REV_OFF, STATE_ADMIN, or NATL_ADMIN.
                    Writes audit entry UPDATE_ROR.
                    Publishes ror.mutation_status_changed when mutation_status flips.
                    Returns RorInternal.

Requirements: 8.1, 8.4
"""

from __future__ import annotations

import json
import logging
from datetime import date

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.audit import write_audit
from core.database import get_db
from core.rbac import UserClaims, check_jurisdiction, require_role
from core.redis_client import get_redis
from core.response_schemas import RorInternal, RorPublic, RorUpdate, mask_owner_name
from core.schemas import Envelope, err, ok
from models.ror import Ror

logger = logging.getLogger(__name__)

router = APIRouter()

# Roles that may write RoR records.
_WRITE_ROLES = ["REV_OFF", "STATE_ADMIN", "NATL_ADMIN"]

# All valid roles — everyone can read RoR.
_ALL_ROLES = ["CITIZEN", "REV_OFF", "REG_OFF", "PLAN_OFF", "TAX_OFF", "STATE_ADMIN", "NATL_ADMIN"]


# ---------------------------------------------------------------------------
# GET /ror/{ulpin}
# ---------------------------------------------------------------------------


@router.get(
    "/{ulpin}",
    response_model=Envelope[RorPublic | RorInternal],
    summary="Fetch RoR record by ULPIN",
)
async def get_ror(
    ulpin: str,
    user: UserClaims = Depends(require_role(_ALL_ROLES)),
    db: AsyncSession = Depends(get_db),
) -> Envelope[RorPublic | RorInternal]:
    """
    Return the Record of Rights for *ulpin*.

    - CITIZEN → RorPublic (owner_name masked)
    - Any officer/admin role → RorInternal (all fields, owner_name unmasked)
    """
    result = await db.execute(select(Ror).where(Ror.ulpin == ulpin))
    ror: Ror | None = result.scalar_one_or_none()

    if ror is None:
        return err(code="NOT_FOUND", message=f"RoR record for ULPIN {ulpin!r} not found")

    if user.role == "CITIZEN":
        payload = RorPublic(
            ulpin=ror.ulpin,
            owner_name=mask_owner_name(ror.owner_name),
            tenure_type=ror.tenure_type,
            khatauni_no=ror.khatauni_no,
            land_use_type=ror.land_use_type,
            mutation_status=ror.mutation_status,
            last_updated=ror.last_updated,
        )
    else:
        payload = RorInternal(
            ulpin=ror.ulpin,
            owner_name=ror.owner_name,
            tenure_type=ror.tenure_type,
            khatauni_no=ror.khatauni_no,
            land_use_type=ror.land_use_type,
            mutation_status=ror.mutation_status,
            last_updated=ror.last_updated,
        )

    return ok(payload)


# ---------------------------------------------------------------------------
# PUT /ror/{ulpin}
# ---------------------------------------------------------------------------


@router.put(
    "/{ulpin}",
    response_model=Envelope[RorInternal],
    summary="Update RoR record by ULPIN",
)
async def update_ror(
    ulpin: str,
    body: RorUpdate,
    user: UserClaims = Depends(require_role(_WRITE_ROLES)),
    _jc: None = Depends(check_jurisdiction),
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
) -> Envelope[RorInternal]:
    """
    Update RoR fields for *ulpin*.

    - Requires REV_OFF, STATE_ADMIN, or NATL_ADMIN.
    - check_jurisdiction enforces that state-scoped officers may only modify
      parcels in their own jurisdiction.
    - Writes an UPDATE_ROR audit entry inside the same DB transaction.
    - Publishes ``ror.mutation_status_changed`` to Redis when mutation_status flips.
    - Returns the updated record as RorInternal.
    """
    result = await db.execute(select(Ror).where(Ror.ulpin == ulpin))
    ror: Ror | None = result.scalar_one_or_none()

    if ror is None:
        return err(code="NOT_FOUND", message=f"RoR record for ULPIN {ulpin!r} not found")

    # Track whether mutation_status will change before we apply the update.
    old_mutation_status: str = ror.mutation_status

    # Apply only the fields supplied in the request body.
    if body.owner_name is not None:
        ror.owner_name = body.owner_name
    if body.tenure_type is not None:
        ror.tenure_type = body.tenure_type
    if body.khatauni_no is not None:
        ror.khatauni_no = body.khatauni_no
    if body.land_use_type is not None:
        ror.land_use_type = body.land_use_type
    if body.mutation_status is not None:
        ror.mutation_status = body.mutation_status

    # Always bump last_updated to today.
    ror.last_updated = date.today()

    # Write audit row inside the same transaction (before commit).
    await write_audit(
        db=db,
        actor_user=user.username,
        actor_role=user.role,
        action="UPDATE_ROR",
        resource_type="ror",
        resource_id=ulpin,
    )

    await db.commit()

    # Publish Redis event if mutation_status flipped (after commit — fire-and-forget).
    new_mutation_status: str = ror.mutation_status
    if body.mutation_status is not None and new_mutation_status != old_mutation_status:
        event_payload = json.dumps({"ulpin": ulpin, "new_status": new_mutation_status})
        try:
            await redis.publish("ror.mutation_status_changed", event_payload)
        except Exception:
            # Non-fatal: log and continue — the DB state is already committed.
            logger.exception(
                "Failed to publish ror.mutation_status_changed for ULPIN %r", ulpin
            )

    response_data = RorInternal(
        ulpin=ror.ulpin,
        owner_name=ror.owner_name,
        tenure_type=ror.tenure_type,
        khatauni_no=ror.khatauni_no,
        land_use_type=ror.land_use_type,
        mutation_status=ror.mutation_status,
        last_updated=ror.last_updated,
    )

    return ok(response_data)
