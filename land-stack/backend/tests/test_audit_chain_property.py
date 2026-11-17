"""
test_audit_chain_property.py — Property-based test for audit log hash chain integrity.

Property 2: Hash chain integrity
  Verify that `prev_hash` linkage is correct across consecutive audit log rows.

Validates: Requirements 6.2, 6.3

The test spins up an in-memory SQLite async database (via aiosqlite) so that no
live PostgreSQL instance is required.  For each Hypothesis example it:

  1. Creates a fresh schema (audit_logs table).
  2. Calls `write_audit` N times in sequence, committing each write.
  3. Reads all rows back in insertion order.
  4. Asserts the three chain-integrity invariants:
       a. The first row's `prev_hash` is "0" * 64 (genesis hash).
       b. Every subsequent row's `prev_hash` equals the preceding row's `hash`.
       c. Every `hash` is a non-empty 64-character lowercase hex string.
"""

from __future__ import annotations

import sys
import os
import importlib

# Allow importing backend/ modules directly (e.g. `from core.audit import ...`).
_backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, _backend_dir)

# Import AuditLog directly from its own module file to avoid triggering
# models/__init__.py, which loads models.parcel (requires geoalchemy2 / PostGIS).
# We load the submodule independently so SQLAlchemy sees it without the geo type.
_audit_log_mod = importlib.import_module("models.audit_log")
AuditLog = _audit_log_mod.AuditLog

# core.audit imports models.audit_log via the same path — register it in
# sys.modules under the backend-prefixed name too so both aliases resolve to
# the same class (needed for SQLAlchemy mapper identity).
sys.modules.setdefault("backend.models.audit_log", _audit_log_mod)

import asyncio
import re

import pytest
from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st
from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from models.audit_log import AuditLog
from core.audit import GENESIS_HASH, write_audit


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_HEX_RE = re.compile(r"^[0-9a-f]{64}$")

# ---------------------------------------------------------------------------
# In-memory SQLite async engine helper
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
    """Create only the audit_logs table in the in-memory SQLite database.

    Using Base.metadata.create_all would also try to create models with
    PostGIS geometry columns (e.g. Parcel), which fails on SQLite because
    SpatiaLite's RecoverGeometryColumn is not available. We only need the
    audit_logs table for this test, so create it directly.
    """
    async with engine.begin() as conn:
        await conn.run_sync(AuditLog.__table__.create)


async def _teardown(engine) -> None:
    """Drop the audit_logs table and dispose the engine."""
    async with engine.begin() as conn:
        await conn.run_sync(AuditLog.__table__.drop)
    await engine.dispose()


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

_printable_text = st.text(
    alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd")),
    min_size=1,
    max_size=30,
)

_audit_event = st.fixed_dictionaries(
    {
        "actor_user": _printable_text,
        "actor_role": st.sampled_from(
            ["REV_OFF", "REG_OFF", "TAX_OFF", "PLAN_OFF", "STATE_ADMIN", "NATL_ADMIN", "CITIZEN"]
        ),
        "action": st.sampled_from(
            [
                "CREATE_PARCEL",
                "UPDATE_ROR",
                "REGISTER_DEED",
                "CREATE_ENCUMBRANCE",
                "UPDATE_ZONING",
                "REASSESS_TAX",
                "ML_FRAUD_SCORE",
            ]
        ),
        "resource_type": st.sampled_from(
            ["parcel", "ror", "registration", "encumbrance", "zoning", "tax"]
        ),
        "resource_id": _printable_text,
    }
)

# Generate between 1 and 10 sequential audit events per test run.
_audit_sequence = st.lists(_audit_event, min_size=1, max_size=10)


# ---------------------------------------------------------------------------
# Core async test logic (run synchronously via asyncio.run inside each test)
# ---------------------------------------------------------------------------

async def _run_chain_test(events: list[dict]) -> None:
    """
    Write all events through write_audit, then verify hash chain integrity.

    Each write_audit call is committed individually (simulating real usage
    where the caller's transaction commits before the next request arrives).
    """
    engine, factory = _make_sqlite_engine()
    await _bootstrap(engine)

    try:
        for event in events:
            async with factory() as db:
                await write_audit(
                    db,
                    actor_user=event["actor_user"],
                    actor_role=event["actor_role"],
                    action=event["action"],
                    resource_type=event["resource_type"],
                    resource_id=event["resource_id"],
                )
                await db.commit()

        # Read all rows in insertion order.
        async with factory() as db:
            result = await db.execute(
                select(AuditLog).order_by(AuditLog.id.asc())
            )
            rows: list[AuditLog] = result.scalars().all()

        assert len(rows) == len(events), (
            f"Expected {len(events)} audit rows, found {len(rows)}"
        )

        for i, row in enumerate(rows):
            # Invariant c: every hash is a 64-char lowercase hex string.
            assert _HEX_RE.match(row.hash), (
                f"Row {i} hash '{row.hash}' is not a 64-char hex string"
            )

            if i == 0:
                # Invariant a: first row's prev_hash is the genesis hash.
                assert row.prev_hash == GENESIS_HASH, (
                    f"First row prev_hash '{row.prev_hash}' != GENESIS_HASH"
                )
            else:
                # Invariant b: each row's prev_hash equals the preceding row's hash.
                assert row.prev_hash == rows[i - 1].hash, (
                    f"Row {i} prev_hash '{row.prev_hash}' "
                    f"!= row {i-1} hash '{rows[i-1].hash}'"
                )

    finally:
        await _teardown(engine)


# ---------------------------------------------------------------------------
# Property 2: Hash chain integrity
# ---------------------------------------------------------------------------

# Property 2: Hash chain integrity
@given(events=_audit_sequence)
@settings(
    max_examples=50,
    suppress_health_check=[HealthCheck.too_slow],
)
def test_audit_hash_chain_integrity(events: list[dict]) -> None:
    """
    **Validates: Requirements 6.2, 6.3**

    For N sequential audit writes:
      1. The first row's `prev_hash` MUST equal GENESIS_HASH ("0" * 64).
      2. Each subsequent row's `prev_hash` MUST equal the preceding row's `hash`.
      3. Every `hash` MUST be a non-empty 64-character lowercase hex string.
    """
    asyncio.run(_run_chain_test(events))
