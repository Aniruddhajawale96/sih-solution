"""
routers/workflow.py — Workflow domain router.

Endpoints
---------
GET  /workflow/tasks               — List workflow tasks scoped to the caller's role +
                                     jurisdiction. CITIZEN → 403.
POST /workflow/{task_id}/approve   — Approve a pending task; writes audit + publishes event.
POST /workflow/{task_id}/reject    — Reject a pending task; writes audit.
GET  /workflow/events/stream       — SSE stream of workflow events from Redis pub/sub.

Role-scoping rules for GET /workflow/tasks:
  NATL_ADMIN    → all tasks
  STATE_ADMIN   → tasks where parcel.state_code == user.jurisdiction
  REV_OFF       → tasks where assigned_role == "REV_OFF" (+ own jurisdiction)
  REG_OFF       → tasks where assigned_role == "REG_OFF" (+ own jurisdiction)
  PLAN_OFF      → tasks where assigned_role == "PLAN_OFF" (+ own jurisdiction)
  TAX_OFF       → tasks where assigned_role == "TAX_OFF" (+ own jurisdiction)
  CITIZEN       → 403

Approve/Reject role rules (per RBAC_MATRIX.md):
  MUTATION task → REV_OFF, STATE_ADMIN, NATL_ADMIN
  ZONING task   → PLAN_OFF, STATE_ADMIN, NATL_ADMIN
  TAX task      → TAX_OFF, STATE_ADMIN, NATL_ADMIN

Requirements: 8.1, 9.1, 9.2
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import AsyncGenerator

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.audit import write_audit
from core.database import get_db
from core.rbac import UserClaims, get_current_user, require_role
from core.redis_client import get_redis
from core.response_schemas import (
    WorkflowActionResponse,
    WorkflowApproveRequest,
    WorkflowRejectRequest,
    WorkflowTask as WorkflowTaskSchema,
)
from core.schemas import Envelope, ok
from models.parcel import Parcel
from models.workflow import WorkflowTask

logger = logging.getLogger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# Role constants
# ---------------------------------------------------------------------------

# All roles that may access workflow endpoints (not CITIZEN)
_OFFICER_ROLES = ["REV_OFF", "REG_OFF", "PLAN_OFF", "TAX_OFF", "STATE_ADMIN", "NATL_ADMIN"]

# Admin roles that may approve/reject any task type
_ADMIN_ROLES = {"STATE_ADMIN", "NATL_ADMIN"}

# Mapping: task_type → which officer role owns the approval
_TASK_APPROVER: dict[str, str] = {
    "MUTATION": "REV_OFF",
    "ZONING":   "PLAN_OFF",
    "TAX":      "TAX_OFF",
}

# SSE channels to subscribe to
_SSE_CHANNELS = (
    "mutation.approved",
    "zoning.approved",
    "tax.approved",
    "registration.completed",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _to_schema(task: WorkflowTask) -> WorkflowTaskSchema:
    """Serialise a WorkflowTask ORM instance to its Pydantic schema."""
    return WorkflowTaskSchema.model_validate(task)


def _audit_action(task_type: str, verdict: str) -> str:
    """Derive the audit action string from task type and verdict.

    task_type ∈ {MUTATION, ZONING, TAX}
    verdict   ∈ {APPROVE, REJECT}
    """
    return f"{verdict}_{task_type}"


def _redis_channel(task_type: str) -> str:
    """Return the Redis channel name for a resolved task type."""
    return f"{task_type.lower()}.approved"


def _check_approver_role(task: WorkflowTask, user: UserClaims) -> None:
    """Raise HTTP 403 if the user may not approve/reject this task type.

    Raises
    ------
    HTTPException (403)
        When the user's role does not match the task's required approver role
        and the user is not STATE_ADMIN or NATL_ADMIN.
    """
    if user.role in _ADMIN_ROLES:
        return  # admins can approve any task type

    required_role = _TASK_APPROVER.get(task.task_type)
    if required_role is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown task_type {task.task_type!r}",
        )
    if user.role != required_role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"Task type {task.task_type!r} requires role {required_role!r}. "
                f"Your role is {user.role!r}."
            ),
        )


# ---------------------------------------------------------------------------
# GET /workflow/tasks
# ---------------------------------------------------------------------------

@router.get(
    "/tasks",
    response_model=Envelope[list[WorkflowTaskSchema]],
    summary="List workflow tasks scoped to caller role/jurisdiction",
)
async def list_tasks(
    task_status: str | None = Query(
        default=None,
        alias="status",
        description="Filter by task status (pending, approved, rejected)",
    ),
    assigned_role: str | None = Query(
        default=None,
        description="Filter by assigned_role",
    ),
    user: UserClaims = Depends(require_role(_OFFICER_ROLES)),
    db: AsyncSession = Depends(get_db),
) -> Envelope[list[WorkflowTaskSchema]]:
    """Return workflow tasks visible to the authenticated caller.

    Scoping rules:
    - **NATL_ADMIN**: all tasks across all states.
    - **STATE_ADMIN**: tasks for parcels in the admin's jurisdiction (state_code).
    - **REV_OFF / REG_OFF / PLAN_OFF / TAX_OFF**: tasks where
      ``assigned_role == user.role`` and (if jurisdiction is set) the parcel
      belongs to the officer's state.
    - **CITIZEN**: 403 (enforced by ``require_role``).
    """
    stmt = select(WorkflowTask)

    if user.role == "NATL_ADMIN":
        # No jurisdiction restriction — sees everything.
        pass

    elif user.role == "STATE_ADMIN":
        # Join to parcels to scope to the admin's jurisdiction.
        if user.jurisdiction:
            stmt = stmt.join(Parcel, WorkflowTask.ulpin == Parcel.ulpin).where(
                Parcel.state_code == user.jurisdiction
            )

    else:
        # Role-based officer: scope to their own assigned_role.
        stmt = stmt.where(WorkflowTask.assigned_role == user.role)
        # Also scope to jurisdiction when present.
        if user.jurisdiction:
            stmt = stmt.join(Parcel, WorkflowTask.ulpin == Parcel.ulpin).where(
                Parcel.state_code == user.jurisdiction
            )

    # Optional query-param filters.
    if task_status is not None:
        stmt = stmt.where(WorkflowTask.status == task_status)

    if assigned_role is not None:
        stmt = stmt.where(WorkflowTask.assigned_role == assigned_role)

    result = await db.execute(stmt)
    tasks: list[WorkflowTask] = list(result.scalars().all())
    return ok([_to_schema(t) for t in tasks])


# ---------------------------------------------------------------------------
# POST /workflow/{task_id}/approve
# ---------------------------------------------------------------------------

@router.post(
    "/{task_id}/approve",
    response_model=Envelope[WorkflowActionResponse],
    summary="Approve a workflow task",
)
async def approve_task(
    task_id: int,
    body: WorkflowApproveRequest,
    user: UserClaims = Depends(require_role(_OFFICER_ROLES)),
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
) -> Envelope[WorkflowActionResponse]:
    """Approve a pending workflow task.

    - Returns 404 if the task does not exist.
    - Returns 400 if the task is not in ``pending`` status.
    - Returns 403 if the caller's role does not match the task's required
      approver role (unless STATE_ADMIN or NATL_ADMIN).
    - Writes an audit entry inside the same DB transaction before committing.
    - Publishes ``{task_type.lower()}.approved`` to Redis after commit.
    """
    task: WorkflowTask | None = await db.get(WorkflowTask, task_id)
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow task {task_id} not found",
        )

    if task.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Task {task_id} is already resolved (status={task.status!r})",
        )

    _check_approver_role(task, user)

    # Update the task.
    task.status = "approved"
    task.resolved_at = datetime.now(timezone.utc)
    task.comment = body.comment

    # Audit before commit — flush task changes so the audit row can reference them.
    await db.flush()

    audit_action = _audit_action(task.task_type, "APPROVE")
    await write_audit(
        db=db,
        actor_user=user.username,
        actor_role=user.role,
        action=audit_action,
        resource_type="workflow_task",
        resource_id=str(task_id),
    )

    await db.commit()
    await db.refresh(task)

    # Publish event to Redis (best-effort — do not roll back on failure).
    channel = _redis_channel(task.task_type)
    event_payload = json.dumps(
        {
            "task_id": task_id,
            "ulpin": task.ulpin,
            "task_type": task.task_type,
            "approved_by": user.username,
        }
    )
    try:
        await redis.publish(channel, event_payload)
    except Exception:
        logger.warning("approve_task: failed to publish to Redis channel %s", channel)

    return ok(
        WorkflowActionResponse(
            task_id=task_id,
            status="approved",
            next_event=channel,
        )
    )


# ---------------------------------------------------------------------------
# POST /workflow/{task_id}/reject
# ---------------------------------------------------------------------------

@router.post(
    "/{task_id}/reject",
    response_model=Envelope[WorkflowActionResponse],
    summary="Reject a workflow task",
)
async def reject_task(
    task_id: int,
    body: WorkflowRejectRequest,
    user: UserClaims = Depends(require_role(_OFFICER_ROLES)),
    db: AsyncSession = Depends(get_db),
) -> Envelope[WorkflowActionResponse]:
    """Reject a pending workflow task.

    - Returns 404 if the task does not exist.
    - Returns 400 if the task is not in ``pending`` status.
    - Returns 403 if the caller's role does not match the task's required
      approver role (unless STATE_ADMIN or NATL_ADMIN).
    - Writes an audit entry inside the same DB transaction before committing.
    - No Redis event is published for rejections.
    """
    task: WorkflowTask | None = await db.get(WorkflowTask, task_id)
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow task {task_id} not found",
        )

    if task.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Task {task_id} is already resolved (status={task.status!r})",
        )

    _check_approver_role(task, user)

    # Update the task.
    task.status = "rejected"
    task.resolved_at = datetime.now(timezone.utc)
    task.comment = body.reason

    # Audit before commit.
    await db.flush()

    audit_action = _audit_action(task.task_type, "REJECT")
    await write_audit(
        db=db,
        actor_user=user.username,
        actor_role=user.role,
        action=audit_action,
        resource_type="workflow_task",
        resource_id=str(task_id),
    )

    await db.commit()

    return ok(
        WorkflowActionResponse(
            task_id=task_id,
            status="rejected",
            next_event=None,
        )
    )


# ---------------------------------------------------------------------------
# GET /workflow/events/stream  — SSE
# ---------------------------------------------------------------------------

@router.get(
    "/events/stream",
    summary="SSE stream of workflow events",
    response_class=StreamingResponse,
)
async def stream_events(
    user: UserClaims = Depends(require_role(_OFFICER_ROLES)),
    redis: aioredis.Redis = Depends(get_redis),
) -> StreamingResponse:
    """Server-Sent Events endpoint for real-time workflow notifications.

    Subscribes to Redis channels:
      - ``mutation.approved``
      - ``zoning.approved``
      - ``tax.approved``
      - ``registration.completed``

    Each event is yielded as::

        data: {"channel": "...", "payload": {...}}\n\n

    The connection runs until the client disconnects. CITIZEN → 403.
    """

    async def _event_generator() -> AsyncGenerator[str, None]:
        pubsub = redis.pubsub()
        await pubsub.subscribe(*_SSE_CHANNELS)
        logger.info(
            "SSE client %s subscribed to channels: %s", user.username, _SSE_CHANNELS
        )
        try:
            async for raw_message in pubsub.listen():
                if raw_message["type"] != "message":
                    continue
                channel: str = raw_message["channel"]
                try:
                    payload = json.loads(raw_message["data"])
                except (json.JSONDecodeError, TypeError):
                    payload = {"raw": raw_message["data"]}

                event_data = json.dumps({"channel": channel, "payload": payload})
                yield f"data: {event_data}\n\n"
        except asyncio.CancelledError:
            logger.info("SSE stream cancelled for user %s", user.username)
        finally:
            try:
                await pubsub.unsubscribe(*_SSE_CHANNELS)
            except Exception:
                pass

    return StreamingResponse(
        _event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
