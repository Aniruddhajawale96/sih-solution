"""
tests/test_workflow_consumer.py — Unit tests for the Workflow Engine consumer
handlers (task 10.1).

These tests verify the two event handlers in isolation by injecting a mock
session factory. They do NOT test the infinite Redis subscriber loop (that
is covered by the integration / property tests in tasks 10.3/10.4).

Coverage:
  - registration.completed → creates WorkflowTask(MUTATION, REV_OFF, pending)
  - registration.completed with missing ulpin → no DB write
  - mutation.approved → loads Tax row, recalculates, writes REASSESS_TAX audit, commits
  - mutation.approved with no Tax row → skips reassessment, no audit
  - mutation.approved with missing ulpin → no DB write

Requirements: 9.1, 9.2, 9.3
"""

from __future__ import annotations

import os
import sys
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Allow importing backend/ modules from the tests directory.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from workflow_engine.consumer import (  # noqa: E402
    _CHANNELS,
    _CHANNEL_HANDLERS,
    _handle_mutation_approved,
    _handle_registration_completed,
)


# ---------------------------------------------------------------------------
# Mock session-factory helper
# ---------------------------------------------------------------------------

def _make_session_factory(db_mock):
    """Return a callable that mimics ``async_sessionmaker``.

    The handler does ``async with session_factory() as db:``. We wrap the
    given mock in an ``asynccontextmanager`` so it yields on ``__aenter__``.
    """

    @asynccontextmanager
    async def _factory():
        yield db_mock

    return _factory


# ---------------------------------------------------------------------------
# registration.completed handler
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_registration_completed_creates_mutation_task():
    """
    registration.completed must create a WorkflowTask with task_type=MUTATION,
    assigned_role=REV_OFF, status=pending, and the correct ulpin.

    Validates: Requirements 9.1
    """
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()

    factory = _make_session_factory(db)

    payload = {"ulpin": "CH-UT-000001", "deed_no": "D-001", "registration_id": 1}
    await _handle_registration_completed(payload, factory)

    # Exactly one db.add call with a WorkflowTask
    db.add.assert_called_once()
    task = db.add.call_args.args[0]
    assert task.task_type == "MUTATION"
    assert task.assigned_role == "REV_OFF"
    assert task.status == "pending"
    assert task.ulpin == "CH-UT-000001"

    # Commit must have been called
    db.commit.assert_called_once()


@pytest.mark.anyio
async def test_registration_completed_missing_ulpin_skips_db():
    """
    registration.completed with no ulpin must not touch the database.

    Validates: Requirements 9.1 (robustness)
    """
    db = AsyncMock()
    factory = _make_session_factory(db)

    await _handle_registration_completed({"deed_no": "D-001"}, factory)

    db.add.assert_not_called()
    db.commit.assert_not_called()


# ---------------------------------------------------------------------------
# mutation.approved handler
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_mutation_approved_reassesses_tax_and_writes_audit():
    """
    mutation.approved must load the Tax row, recalculate annual_tax when
    arrears > 0 and area_sqm is provided, write a REASSESS_TAX audit entry,
    and commit.

    Validates: Requirements 9.2
    """
    tax_row = MagicMock()
    tax_row.ulpin = "CH-UT-000001"
    tax_row.annual_tax = 5000
    tax_row.arrears = 1000  # arrears > 0 → recalculate

    # db.execute is called twice:
    #   1) select(Tax)  → scalar_one_or_none() returns tax_row
    #   2) select(AuditLog.hash) inside write_audit → scalar_one_or_none() returns None
    # NOTE: scalar_one_or_none() is a synchronous SQLAlchemy method, so use MagicMock.
    tax_result = MagicMock()
    tax_result.scalar_one_or_none = MagicMock(return_value=tax_row)

    audit_hash_result = MagicMock()
    audit_hash_result.scalar_one_or_none = MagicMock(return_value=None)

    db = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()

    call_results = [tax_result, audit_hash_result]
    call_idx = [0]

    async def _execute(*args, **kwargs):
        idx = call_idx[0]
        call_idx[0] += 1
        return call_results[min(idx, len(call_results) - 1)]

    db.execute = _execute

    factory = _make_session_factory(db)

    payload = {"ulpin": "CH-UT-000001", "area_sqm": 250.0}
    await _handle_mutation_approved(payload, factory)

    # annual_tax should have been recalculated: 250 * 10 = 2500
    assert tax_row.annual_tax == 2500

    # db.add called for the audit entry (write_audit adds the AuditLog)
    db.add.assert_called_once()
    audit_entry = db.add.call_args.args[0]
    assert audit_entry.action == "REASSESS_TAX"
    assert audit_entry.resource_type == "tax"
    assert audit_entry.resource_id == "CH-UT-000001"

    # Commit must have been called
    db.commit.assert_called_once()


@pytest.mark.anyio
async def test_mutation_approved_no_recalculation_when_no_arrears():
    """
    mutation.approved must NOT recalculate annual_tax when arrears == 0,
    but must still write the REASSESS_TAX audit entry and commit.

    Validates: Requirements 9.2
    """
    original_tax = 5000
    tax_row = MagicMock()
    tax_row.ulpin = "CH-UT-000001"
    tax_row.annual_tax = original_tax
    tax_row.arrears = 0  # no arrears → no recalculation

    tax_result = MagicMock()
    tax_result.scalar_one_or_none = MagicMock(return_value=tax_row)

    audit_hash_result = MagicMock()
    audit_hash_result.scalar_one_or_none = MagicMock(return_value=None)

    db = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()

    call_results = [tax_result, audit_hash_result]
    call_idx = [0]

    async def _execute(*args, **kwargs):
        idx = call_idx[0]
        call_idx[0] += 1
        return call_results[min(idx, len(call_results) - 1)]

    db.execute = _execute

    factory = _make_session_factory(db)

    payload = {"ulpin": "CH-UT-000001", "area_sqm": 250.0}
    await _handle_mutation_approved(payload, factory)

    # annual_tax unchanged
    assert tax_row.annual_tax == original_tax

    # Audit still written
    db.add.assert_called_once()
    audit_entry = db.add.call_args.args[0]
    assert audit_entry.action == "REASSESS_TAX"

    db.commit.assert_called_once()


@pytest.mark.anyio
async def test_mutation_approved_no_tax_row_skips():
    """
    mutation.approved for a parcel with no Tax row must skip reassessment
    entirely (no audit, no commit).

    Validates: Requirements 9.2 (robustness)
    """
    tax_result = MagicMock()
    tax_result.scalar_one_or_none = MagicMock(return_value=None)

    db = AsyncMock()
    db.execute = AsyncMock(return_value=tax_result)
    db.add = MagicMock()
    db.commit = AsyncMock()

    factory = _make_session_factory(db)

    payload = {"ulpin": "CH-UT-999", "area_sqm": 100.0}
    await _handle_mutation_approved(payload, factory)

    db.add.assert_not_called()
    db.commit.assert_not_called()


@pytest.mark.anyio
async def test_mutation_approved_missing_ulpin_skips_db():
    """
    mutation.approved with no ulpin must not touch the database.

    Validates: Requirements 9.2 (robustness)
    """
    db = AsyncMock()
    factory = _make_session_factory(db)

    await _handle_mutation_approved({"area_sqm": 100.0}, factory)

    db.execute.assert_not_called()
    db.add.assert_not_called()
    db.commit.assert_not_called()


# ---------------------------------------------------------------------------
# Channel/handler registration
# ---------------------------------------------------------------------------


def test_channels_and_handlers_registered():
    """
    The consumer must subscribe to exactly the two documented channels and
    map each to its handler.

    Validates: Requirements 9.1, 9.2
    """
    assert set(_CHANNELS) == {"registration.completed", "mutation.approved"}
    assert _CHANNEL_HANDLERS["registration.completed"] is _handle_registration_completed
    assert _CHANNEL_HANDLERS["mutation.approved"] is _handle_mutation_approved
