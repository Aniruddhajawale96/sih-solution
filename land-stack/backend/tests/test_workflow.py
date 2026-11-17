"""
tests/test_workflow.py — Unit tests for routers/workflow.py.

Validates: Requirements 12.1, 12.2

Covers:
  1. GET  /workflow/tasks         — REV_OFF sees only tasks with assigned_role="REV_OFF"
  2. GET  /workflow/tasks         — NATL_ADMIN sees all tasks
  3. GET  /workflow/tasks         — CITIZEN → 403
  4. POST /workflow/{id}/approve  — REV_OFF approves MUTATION task → 200, status="approved",
                                    audit APPROVE_MUTATION written, Redis publish called
  5. POST /workflow/{id}/approve  — Wrong role (TAX_OFF cannot approve MUTATION) → 403
  6. POST /workflow/{id}/approve  — Task not found → 404
  7. POST /workflow/{id}/approve  — Task already resolved (status="approved") → 400
  8. POST /workflow/{id}/reject   — REV_OFF rejects MUTATION task → 200, status="rejected",
                                    audit REJECT_MUTATION written
  9. GET  /workflow/events/stream — Returns text/event-stream; officer succeeds; CITIZEN → 403

Tests use httpx.AsyncClient with FastAPI ASGI transport.
Dependency overrides replace get_db, get_current_user, and get_redis.
write_audit is patched to avoid DB side effects.
No live PostgreSQL or Redis connection is required.
"""

from __future__ import annotations

import sys
import os
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import httpx
from fastapi import status

# Allow importing backend/ modules from the tests directory.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from main import app
from core.rbac import UserClaims, get_current_user
from core.database import get_db
from core.redis_client import get_redis


# ---------------------------------------------------------------------------
# Shared user-claims factory
# ---------------------------------------------------------------------------

def _make_user(role: str, username: str | None = None, jurisdiction: str | None = None) -> UserClaims:
    name = username or f"user_{role.lower()}"
    return UserClaims(username=name, role=role, jurisdiction=jurisdiction)


# ---------------------------------------------------------------------------
# DB override helper
# ---------------------------------------------------------------------------

def _db_override(db_mock):
    """Return an async-generator dependency override that yields *db_mock*."""
    async def _override():
        yield db_mock
    return _override


# ---------------------------------------------------------------------------
# Minimal WorkflowTask stub
# ---------------------------------------------------------------------------

class _FakeTask:
    """Stand-in for the WorkflowTask SQLAlchemy model."""

    def __init__(
        self,
        id: int = 1,
        ulpin: str = "MH-MUM-001",
        task_type: str = "MUTATION",
        assigned_role: str = "REV_OFF",
        status: str = "pending",
        created_at: datetime | None = None,
        resolved_at: datetime | None = None,
        comment: str | None = None,
    ):
        self.id = id
        self.ulpin = ulpin
        self.task_type = task_type
        self.assigned_role = assigned_role
        self.status = status
        self.created_at = created_at or datetime(2024, 1, 15, tzinfo=timezone.utc)
        self.resolved_at = resolved_at
        self.comment = comment


# ---------------------------------------------------------------------------
# Redis mock helpers
# ---------------------------------------------------------------------------

def _make_redis_mock() -> AsyncMock:
    """Redis mock: not blacklisted, publish no-ops."""
    redis = AsyncMock()
    redis.exists = AsyncMock(return_value=0)   # token not blacklisted
    redis.publish = AsyncMock(return_value=1)
    return redis


def _make_pubsub_redis() -> AsyncMock:
    """Redis mock for SSE stream: pubsub that immediately stops iterating."""
    redis = AsyncMock()
    redis.exists = AsyncMock(return_value=0)

    pubsub = AsyncMock()
    pubsub.subscribe = AsyncMock()
    pubsub.unsubscribe = AsyncMock()

    # Yield no messages so the generator exits quickly
    async def _empty_listen():
        return
        yield  # make it an async generator

    pubsub.listen = _empty_listen
    redis.pubsub = MagicMock(return_value=pubsub)
    return redis


# ---------------------------------------------------------------------------
# DB mock factory for list_tasks
# ---------------------------------------------------------------------------

def _make_db_for_list(tasks: list[_FakeTask]) -> AsyncMock:
    """AsyncSession mock that returns *tasks* from db.execute(select(WorkflowTask))."""
    db = AsyncMock()

    scalars_mock = MagicMock()
    scalars_mock.all = MagicMock(return_value=tasks)

    exec_result = MagicMock()
    exec_result.scalars = MagicMock(return_value=scalars_mock)

    db.execute = AsyncMock(return_value=exec_result)
    return db


# ---------------------------------------------------------------------------
# DB mock factory for approve / reject
# ---------------------------------------------------------------------------

def _make_db_for_action(task: _FakeTask | None) -> AsyncMock:
    """AsyncSession mock for approve/reject endpoints.

    db.get() returns *task* (or None for not-found tests).
    flush/commit/refresh are no-ops.
    """
    db = AsyncMock()
    db.get = AsyncMock(return_value=task)
    db.flush = AsyncMock()
    db.commit = AsyncMock()

    async def _refresh(obj):
        pass  # task attributes already set in-place

    db.refresh = AsyncMock(side_effect=_refresh)
    return db


# ===========================================================================
# 1. GET /workflow/tasks — REV_OFF sees only assigned_role="REV_OFF" tasks
# ===========================================================================

@pytest.mark.anyio
async def test_list_tasks_rev_off_sees_own_role_only():
    """
    GET /workflow/tasks by REV_OFF must return only tasks where
    assigned_role == "REV_OFF".

    Requirements: 12.1, 12.2
    """
    rev_task = _FakeTask(id=1, assigned_role="REV_OFF")
    # Simulate the DB already filtered by the router's `where` clause
    db = _make_db_for_list([rev_task])

    app.dependency_overrides[get_db] = _db_override(db)
    app.dependency_overrides[get_redis] = lambda: _make_redis_mock()
    app.dependency_overrides[get_current_user] = lambda: _make_user("REV_OFF", jurisdiction="MH")

    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as ac:
            resp = await ac.get("/api/v1/workflow/tasks")
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == status.HTTP_200_OK, resp.text
    body = resp.json()
    assert body["success"] is True
    items = body["data"]
    assert len(items) == 1
    assert items[0]["assigned_role"] == "REV_OFF"


# ===========================================================================
# 2. GET /workflow/tasks — NATL_ADMIN sees all tasks
# ===========================================================================

@pytest.mark.anyio
async def test_list_tasks_natl_admin_sees_all():
    """
    GET /workflow/tasks by NATL_ADMIN must return every task regardless of
    assigned_role or jurisdiction.

    Requirements: 12.1
    """
    tasks = [
        _FakeTask(id=1, assigned_role="REV_OFF"),
        _FakeTask(id=2, assigned_role="TAX_OFF", task_type="TAX"),
        _FakeTask(id=3, assigned_role="PLAN_OFF", task_type="ZONING"),
    ]
    db = _make_db_for_list(tasks)

    app.dependency_overrides[get_db] = _db_override(db)
    app.dependency_overrides[get_redis] = lambda: _make_redis_mock()
    app.dependency_overrides[get_current_user] = lambda: _make_user("NATL_ADMIN")

    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as ac:
            resp = await ac.get("/api/v1/workflow/tasks")
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == status.HTTP_200_OK, resp.text
    body = resp.json()
    assert body["success"] is True
    assert len(body["data"]) == 3


# ===========================================================================
# 3. GET /workflow/tasks — CITIZEN → 403
# ===========================================================================

@pytest.mark.anyio
async def test_list_tasks_citizen_returns_403():
    """
    GET /workflow/tasks by CITIZEN must return 403.

    Requirements: 12.2
    """
    db = _make_db_for_list([])

    app.dependency_overrides[get_db] = _db_override(db)
    app.dependency_overrides[get_redis] = lambda: _make_redis_mock()
    app.dependency_overrides[get_current_user] = lambda: _make_user("CITIZEN")

    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as ac:
            resp = await ac.get("/api/v1/workflow/tasks")
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == status.HTTP_403_FORBIDDEN
    body = resp.json()
    assert body["success"] is False


# ===========================================================================
# 4. POST /workflow/{id}/approve — REV_OFF approves MUTATION task
#    → 200, status="approved", audit APPROVE_MUTATION written, Redis publish called
# ===========================================================================

@pytest.mark.anyio
async def test_approve_mutation_by_rev_off_succeeds():
    """
    POST /workflow/{task_id}/approve by REV_OFF on a MUTATION/pending task must:
      - return 200
      - return status="approved" in the response envelope
      - call write_audit with action="APPROVE_MUTATION"
      - call redis.publish on the "mutation.approved" channel

    Requirements: 12.1
    """
    task = _FakeTask(id=10, task_type="MUTATION", assigned_role="REV_OFF", status="pending")
    db = _make_db_for_action(task)
    redis = _make_redis_mock()

    app.dependency_overrides[get_db] = _db_override(db)
    app.dependency_overrides[get_redis] = lambda: redis
    app.dependency_overrides[get_current_user] = lambda: _make_user("REV_OFF", "officer1", "MH")

    with patch("routers.workflow.write_audit", new_callable=AsyncMock) as mock_audit:
        try:
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as ac:
                resp = await ac.post(
                    "/api/v1/workflow/10/approve",
                    json={"comment": "Looks good"},
                )
        finally:
            app.dependency_overrides.clear()

    assert resp.status_code == status.HTTP_200_OK, resp.text
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["task_id"] == 10
    assert body["data"]["status"] == "approved"

    # Audit must have been written with correct action
    mock_audit.assert_called_once()
    kw = mock_audit.call_args.kwargs
    assert kw["action"] == "APPROVE_MUTATION"
    assert kw["actor_role"] == "REV_OFF"
    assert kw["resource_type"] == "workflow_task"
    assert kw["resource_id"] == "10"

    # Redis publish must have been called on mutation.approved channel
    redis.publish.assert_called_once()
    channel_arg = redis.publish.call_args.args[0]
    assert channel_arg == "mutation.approved"


# ===========================================================================
# 5. POST /workflow/{id}/approve — Wrong role (TAX_OFF cannot approve MUTATION) → 403
# ===========================================================================

@pytest.mark.anyio
async def test_approve_mutation_wrong_role_returns_403():
    """
    POST /workflow/{task_id}/approve by TAX_OFF on a MUTATION task must return 403.
    TAX_OFF only owns TAX tasks.

    Requirements: 12.2
    """
    task = _FakeTask(id=11, task_type="MUTATION", assigned_role="REV_OFF", status="pending")
    db = _make_db_for_action(task)

    app.dependency_overrides[get_db] = _db_override(db)
    app.dependency_overrides[get_redis] = lambda: _make_redis_mock()
    app.dependency_overrides[get_current_user] = lambda: _make_user("TAX_OFF", jurisdiction="MH")

    with patch("routers.workflow.write_audit", new_callable=AsyncMock):
        try:
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as ac:
                resp = await ac.post(
                    "/api/v1/workflow/11/approve",
                    json={"comment": "Trying to approve"},
                )
        finally:
            app.dependency_overrides.clear()

    assert resp.status_code == status.HTTP_403_FORBIDDEN, resp.text
    body = resp.json()
    assert body["success"] is False


# ===========================================================================
# 6. POST /workflow/{id}/approve — Task not found → 404
# ===========================================================================

@pytest.mark.anyio
async def test_approve_task_not_found_returns_404():
    """
    POST /workflow/{task_id}/approve when the task does not exist must return 404.

    Requirements: 12.2
    """
    db = _make_db_for_action(None)  # db.get returns None

    app.dependency_overrides[get_db] = _db_override(db)
    app.dependency_overrides[get_redis] = lambda: _make_redis_mock()
    app.dependency_overrides[get_current_user] = lambda: _make_user("REV_OFF", jurisdiction="MH")

    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as ac:
            resp = await ac.post(
                "/api/v1/workflow/9999/approve",
                json={"comment": "Approve missing task"},
            )
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == status.HTTP_404_NOT_FOUND, resp.text
    body = resp.json()
    assert body["success"] is False


# ===========================================================================
# 7. POST /workflow/{id}/approve — Task already resolved (status="approved") → 400
# ===========================================================================

@pytest.mark.anyio
async def test_approve_already_resolved_task_returns_400():
    """
    POST /workflow/{task_id}/approve on a task that is already "approved"
    must return 400 (already resolved).

    Requirements: 12.2
    """
    task = _FakeTask(
        id=12,
        task_type="MUTATION",
        assigned_role="REV_OFF",
        status="approved",  # already resolved
    )
    db = _make_db_for_action(task)

    app.dependency_overrides[get_db] = _db_override(db)
    app.dependency_overrides[get_redis] = lambda: _make_redis_mock()
    app.dependency_overrides[get_current_user] = lambda: _make_user("REV_OFF", jurisdiction="MH")

    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as ac:
            resp = await ac.post(
                "/api/v1/workflow/12/approve",
                json={"comment": "Re-approve"},
            )
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == status.HTTP_400_BAD_REQUEST, resp.text
    body = resp.json()
    assert body["success"] is False


# ===========================================================================
# 8. POST /workflow/{id}/reject — REV_OFF rejects MUTATION task
#    → 200, status="rejected", audit REJECT_MUTATION written
# ===========================================================================

@pytest.mark.anyio
async def test_reject_mutation_by_rev_off_succeeds():
    """
    POST /workflow/{task_id}/reject by REV_OFF on a MUTATION/pending task must:
      - return 200
      - return status="rejected" in the response envelope
      - call write_audit with action="REJECT_MUTATION"

    Requirements: 12.1
    """
    task = _FakeTask(id=20, task_type="MUTATION", assigned_role="REV_OFF", status="pending")
    db = _make_db_for_action(task)

    app.dependency_overrides[get_db] = _db_override(db)
    app.dependency_overrides[get_redis] = lambda: _make_redis_mock()
    app.dependency_overrides[get_current_user] = lambda: _make_user("REV_OFF", "officer2", "MH")

    with patch("routers.workflow.write_audit", new_callable=AsyncMock) as mock_audit:
        try:
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as ac:
                resp = await ac.post(
                    "/api/v1/workflow/20/reject",
                    json={"reason": "Incomplete documents"},
                )
        finally:
            app.dependency_overrides.clear()

    assert resp.status_code == status.HTTP_200_OK, resp.text
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["task_id"] == 20
    assert body["data"]["status"] == "rejected"

    # Audit must have been written with correct action
    mock_audit.assert_called_once()
    kw = mock_audit.call_args.kwargs
    assert kw["action"] == "REJECT_MUTATION"
    assert kw["actor_role"] == "REV_OFF"
    assert kw["resource_type"] == "workflow_task"
    assert kw["resource_id"] == "20"


# ===========================================================================
# 9a. GET /workflow/events/stream — Officer role gets text/event-stream
# ===========================================================================

@pytest.mark.anyio
async def test_sse_stream_officer_gets_event_stream_content_type():
    """
    GET /workflow/events/stream by an officer role must return a response
    with Content-Type: text/event-stream.

    Requirements: 12.1
    """
    redis = _make_pubsub_redis()

    app.dependency_overrides[get_redis] = lambda: redis
    app.dependency_overrides[get_current_user] = lambda: _make_user("REV_OFF", jurisdiction="MH")

    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as ac:
            resp = await ac.get("/api/v1/workflow/events/stream")
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == status.HTTP_200_OK, resp.text
    assert "text/event-stream" in resp.headers.get("content-type", "")


# ===========================================================================
# 9b. GET /workflow/events/stream — CITIZEN → 403
# ===========================================================================

@pytest.mark.anyio
async def test_sse_stream_citizen_returns_403():
    """
    GET /workflow/events/stream by CITIZEN must return 403.

    Requirements: 12.2
    """
    redis = _make_pubsub_redis()

    app.dependency_overrides[get_redis] = lambda: redis
    app.dependency_overrides[get_current_user] = lambda: _make_user("CITIZEN")

    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as ac:
            resp = await ac.get("/api/v1/workflow/events/stream")
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == status.HTTP_403_FORBIDDEN
    body = resp.json()
    assert body["success"] is False
