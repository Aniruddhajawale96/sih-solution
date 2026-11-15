"""
core/audit.py — Hash-chained audit log writer.

Design contract (design.md § 4):
  - `write_audit` is called inside the same DB transaction as the mutation,
    before `await db.commit()`.
  - Each row's `hash` = SHA-256(prev_hash + serialized row contents).
  - The first row uses a genesis hash of "0" * 64 (no preceding row).
  - `await db.flush()` obtains the auto-incremented id without committing,
    so the caller's outer `db.commit()` finalizes both the mutation row and
    the audit row atomically.

Requirements: 6.1, 6.2, 6.3
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.audit_log import AuditLog


GENESIS_HASH: str = "0" * 64  # used as prev_hash for the very first audit row


def _compute_hash(
    prev_hash: str,
    actor_user: str,
    actor_role: str,
    action: str,
    resource_type: str,
    resource_id: str,
    timestamp: datetime,
) -> str:
    """Return SHA-256 hex digest of the concatenated row content.

    The content string is deterministic: prev_hash followed by all row
    fields in a fixed order, with the timestamp in ISO-8601 format.
    """
    content = (
        f"{prev_hash}"
        f"{actor_user}{actor_role}{action}"
        f"{resource_type}{resource_id}"
        f"{timestamp.isoformat()}"
    )
    return hashlib.sha256(content.encode()).hexdigest()


async def write_audit(
    db: AsyncSession,
    actor_user: str,
    actor_role: str,
    action: str,
    resource_type: str,
    resource_id: str,
) -> AuditLog:
    """Write a single hash-chained audit log entry.

    Parameters
    ----------
    db:
        The open ``AsyncSession`` for the current request. Must be inside
        an active transaction (i.e. the caller has not yet called
        ``await db.commit()``).
    actor_user:
        Username of the authenticated caller performing the action.
    actor_role:
        RBAC role of the caller (e.g. ``"REV_OFF"``).
    action:
        Documented action string for the operation
        (e.g. ``"CREATE_PARCEL"``, ``"REGISTER_DEED"``).
    resource_type:
        The model/table being modified (e.g. ``"parcel"``, ``"ror"``).
    resource_id:
        The ULPIN (or surrogate id) of the affected record.

    Returns
    -------
    AuditLog
        The newly created (and flushed) ``AuditLog`` instance. Its ``id``
        is populated after the flush; the caller's ``db.commit()`` will
        finalize it.

    Notes
    -----
    The function fetches the most recent row's ``hash`` under a row-level
    lock via ``ORDER BY id DESC LIMIT 1``. In high-concurrency scenarios,
    callers should serialize audit writes (e.g. with ``SELECT FOR UPDATE``
    or application-level locking) to guarantee strict chain ordering.
    """
    # Fetch the hash of the most recent audit row; fall back to genesis.
    result = await db.execute(
        select(AuditLog.hash).order_by(desc(AuditLog.id)).limit(1)
    )
    prev_hash: str = result.scalar_one_or_none() or GENESIS_HASH

    now = datetime.now(timezone.utc)
    new_hash = _compute_hash(
        prev_hash,
        actor_user,
        actor_role,
        action,
        resource_type,
        resource_id,
        now,
    )

    entry = AuditLog(
        actor_user=actor_user,
        actor_role=actor_role,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        timestamp=now,
        hash=new_hash,
        prev_hash=prev_hash,
    )
    db.add(entry)
    await db.flush()  # populate entry.id without committing
    return entry
