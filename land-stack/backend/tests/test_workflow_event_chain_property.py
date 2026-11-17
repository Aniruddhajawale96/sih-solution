"""
test_workflow_event_chain_property.py — Property-based test for workflow event chain.

Property 8: Workflow event chain
  Verify that for any `registration.completed` Redis event carrying a valid `ulpin`,
  the consumer creates exactly one WorkflowTask row of task_type="MUTATION" with
  assigned_role="REV_OFF" and status="pending" matching that ulpin.

# Property 8: Workflow event chain — Validates Requirements 9.1

The test spins up an in-memory SQLite async database (via aiosqlite) so that no
live PostgreSQL instance or Redis connection is required.  For each Hypothesis
example it:

  1. Creates a fresh schema (workflow_tasks table only; SQLite FK enforcement is
     off by default, so the parcels FK is never checked).
  2. Calls `_handle_registration_completed({"ulpin": ulpin}, session_factory)`
     directly — no Redis involved.
  3. Queries the DB and asserts exactly one WorkflowTask row exists with
     task_type="MUTATION", assigned_role="REV_OFF", status="pending", ulpin==ulpin.
  4. Calls the handler again with the same ulpin and asserts the second call
     creates a second row (no built-in dedup logic in the consumer); the total
     count is 2. This is documented behaviour, not a failure.
"""

from __future__ import annotations

import sys
import os
import importlib
import asyncio

# Allow importing backend/ modules directly (e.g. `from models.workflow import ...`).
_backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, _backend_dir)

# Import WorkflowTask directly from its own module file to avoid triggering
# models/__init__.py, which loads models.parcel (requires geoalchemy2 / PostGIS).
_workflow_mod = importlib.import_module("models.workflow")
WorkflowTask = _workflow_mod.WorkflowTask

# Register under the backend-prefixed alias too so both resolve to the same class.
sys.modules.setdefault("backend.models.workflow", _workflow_mod)

import pytest
from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

# Import the internal handler directly — no Redis, no pub/sub.
from workflow_engine.consumer import _handle_registration_completed


# ---------------------------------------------------------------------------
# In-memory SQLite async engine helper  (same pattern as test_audit_chain_property.py)
# ---------------------------------------------------------------------------

def _make_sqlite_engine():
    """Return a fresh in-memory aiosqlite engine and session factory."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
    )
    factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )
    return engine, factory


async def _bootstrap(engine) -> None:
    """Create the workflow_tasks table in the in-memory SQLite database.

    WorkflowTask has a FK to parcels.ulpin, but SQLite has FK enforcement
    disabled by default, so we can create workflow_tasks alone without a
    parcels table and inserts will succeed.
    """
    async with engine.begin() as conn:
        await conn.run_sync(WorkflowTask.__table__.create)


async def _teardown(engine) -> None:
    """Drop the workflow_tasks table and dispose the engine."""
    async with engine.begin() as conn:
        await conn.run_sync(WorkflowTask.__table__.drop)
    await engine.dispose()


# ---------------------------------------------------------------------------
# Core async test logic
# ---------------------------------------------------------------------------

async def _run_workflow_event_chain_test(ulpin: str) -> None:
    """
    Call the registration.completed handler and verify WorkflowTask creation.

    Steps:
    1. Bootstrap a fresh in-memory DB.
    2. Call handler once — assert exactly 1 matching WorkflowTask row.
    3. Call handler again (same ulpin) — assert 2 rows total (no dedup logic).
    """
    engine, factory = _make_sqlite_engine()
    await _bootstrap(engine)

    try:
        # --- First call: must create exactly one WorkflowTask ---
        await _handle_registration_completed({"ulpin": ulpin}, factory)

        async with factory() as db:
            result = await db.execute(
                select(WorkflowTask).where(WorkflowTask.ulpin == ulpin)
            )
            rows = result.scalars().all()

        assert len(rows) == 1, (
            f"Expected 1 WorkflowTask after first call for ulpin={ulpin!r}, "
            f"found {len(rows)}"
        )

        row = rows[0]
        assert row.task_type == "MUTATION", (
            f"task_type expected 'MUTATION', got {row.task_type!r}"
        )
        assert row.assigned_role == "REV_OFF", (
            f"assigned_role expected 'REV_OFF', got {row.assigned_role!r}"
        )
        assert row.status == "pending", (
            f"status expected 'pending', got {row.status!r}"
        )
        assert row.ulpin == ulpin, (
            f"ulpin expected {ulpin!r}, got {row.ulpin!r}"
        )

        # --- Second call with same ulpin: consumer has no dedup logic ---
        # The count becomes 2; this is documented behaviour, not a bug in the test.
        await _handle_registration_completed({"ulpin": ulpin}, factory)

        async with factory() as db:
            result = await db.execute(
                select(WorkflowTask).where(WorkflowTask.ulpin == ulpin)
            )
            rows_after_second = result.scalars().all()

        # NOTE: The consumer does not implement deduplication for
        # registration.completed events, so a second call produces a second row.
        assert len(rows_after_second) == 2, (
            f"Expected 2 WorkflowTask rows after second call for ulpin={ulpin!r}, "
            f"found {len(rows_after_second)}"
        )
        for r in rows_after_second:
            assert r.task_type == "MUTATION"
            assert r.assigned_role == "REV_OFF"
            assert r.status == "pending"

    finally:
        await _teardown(engine)


# ---------------------------------------------------------------------------
# Property 8: Workflow event chain — Validates Requirements 9.1
# ---------------------------------------------------------------------------

# Property 8: Workflow event chain — Validates Requirements 9.1
@given(ulpin=st.text(min_size=1, max_size=50).filter(lambda s: s.strip()))
@settings(
    max_examples=50,
    suppress_health_check=[HealthCheck.too_slow],
)
def test_workflow_event_chain_creates_mutation_task(ulpin: str) -> None:
    """
    **Validates: Requirements 9.1**

    For any registration.completed event carrying a valid ulpin:
      1. Exactly one WorkflowTask row is created with
         task_type="MUTATION", assigned_role="REV_OFF", status="pending",
         and ulpin matching the event payload.
      2. A second call with the same ulpin creates a second row (the consumer
         has no dedup logic; count becomes 2). This is documented behaviour.
    """
    asyncio.run(_run_workflow_event_chain_test(ulpin))
