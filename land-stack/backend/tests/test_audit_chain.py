"""
test_audit_chain.py — Property-based test for audit log hash chain integrity.

**Property 2: Hash chain integrity**
  Verify that `prev_hash` linkage is correct across consecutive audit log rows.

**Validates: Requirements 6.2, 6.3**

The test uses an in-memory SQLite async database (aiosqlite) so no live
PostgreSQL instance is required.  For each Hypothesis example it:

  1. Creates a fresh schema (audit_logs table only).
  2. Calls `write_audit` N times in sequence, committing after each write.
  3. Reads all rows back in insertion order (by id).
  4. Asserts three chain-integrity invariants:
       a. The first row's `prev_hash` is GENESIS_HASH ("0" * 64).
       b. Every subsequent row's `prev_hash` equals the preceding row's `hash`.
       c. Every `hash` is a 64-character lowercase hex string.
"""

from __future__ import annotations

import asyncio
import os
import re
import sys

# ---------------------------------------------------------------------------
# Path setup — make both `backend` (as a package) and submodules importable.
# When pytest runs from backend/, "." is on sys.path, so `core.*` and
# `models.*` resolve directly.  We also add the parent so `backend.*` aliases
# work if any transitive import uses them.
# ---------------------------------------------------------------------------
_backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_project_dir = os.path.abspath(os.path.join(_backend_dir, ".."))

for _p in (_backend_dir, _project_dir):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# Ensure `backend` package is known to the import system without running the
# models/__init__.py (which re-imports via `backend.*` prefix and can trip up
# in isolated test environments).  We stub `backend` as the actual package
# object from the filesystem but only load the submodules we need.
import importlib
import importlib.util
import types


def _load_module_directly(dotted_name: str, file_path: str) -> types.ModuleType:
    """Load a single .py file as *dotted_name* without running its package __init__."""
    if dotted_name in sys.modules:
        return sys.modules[dotted_name]
    spec = importlib.util.spec_from_file_location(dotted_name, file_path)
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    sys.modules[dotted_name] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


# Stub the top-level `backend` namespace package so `backend.*` imports work.
if "backend" not in sys.modules:
    _backend_pkg = types.ModuleType("backend")
    _backend_pkg.__path__ = [_backend_dir]  # type: ignore[attr-defined]
    _backend_pkg.__package__ = "backend"
    sys.modules["backend"] = _backend_pkg

# Stub `core` and `models` as namespace packages without running their __init__.
for _pkg_name, _pkg_path in [
    ("core", os.path.join(_backend_dir, "core")),
    ("models", os.path.join(_backend_dir, "models")),
    ("backend.core", os.path.join(_backend_dir, "core")),
    ("backend.models", os.path.join(_backend_dir, "models")),
]:
    if _pkg_name not in sys.modules:
        _pkg = types.ModuleType(_pkg_name)
        _pkg.__path__ = [_pkg_path]  # type: ignore[attr-defined]
        _pkg.__package__ = _pkg_name
        sys.modules[_pkg_name] = _pkg

# Load only the specific submodules we need, bypassing their package __init__.
_database_mod = _load_module_directly(
    "core.database", os.path.join(_backend_dir, "core", "database.py")
)
sys.modules.setdefault("backend.core.database", _database_mod)

_audit_log_mod = _load_module_directly(
    "models.audit_log", os.path.join(_backend_dir, "models", "audit_log.py")
)
sys.modules.setdefault("backend.models.audit_log", _audit_log_mod)

_audit_core_mod = _load_module_directly(
    "core.audit", os.path.join(_backend_dir, "core", "audit.py")
)
sys.modules.setdefault("backend.core.audit", _audit_core_mod)

# ---------------------------------------------------------------------------
# Actual test imports
# ---------------------------------------------------------------------------

from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from core.audit import GENESIS_HASH, write_audit
from core.database import Base
from models.audit_log import AuditLog

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_HEX_RE = re.compile(r"^[0-9a-f]{64}$")

# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

_alphanumeric = st.text(
    alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd")),
    min_size=1,
    max_size=30,
)

_audit_event = st.fixed_dictionaries(
    {
        "actor_user": _alphanumeric,
        "actor_role": st.sampled_from(
            [
                "REV_OFF",
                "REG_OFF",
                "TAX_OFF",
                "PLAN_OFF",
                "STATE_ADMIN",
                "NATL_ADMIN",
                "CITIZEN",
            ]
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
        "resource_id": _alphanumeric,
    }
)

# 1–10 sequential audit events per Hypothesis example.
_audit_sequence = st.lists(_audit_event, min_size=1, max_size=10)

# ---------------------------------------------------------------------------
# In-memory SQLite async helpers
# ---------------------------------------------------------------------------


def _make_engine():
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


async def _run_chain_test(events: list[dict]) -> None:
    """
    Write all events through write_audit, then verify hash chain integrity.

    Each write_audit call is committed individually, mirroring real usage
    where each request commits its own transaction.
    """
    engine, factory = _make_engine()

    # Create only the audit_logs table (avoid geo types from other models).
    async with engine.begin() as conn:
        await conn.run_sync(AuditLog.__table__.create)

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
            result = await db.execute(select(AuditLog).order_by(AuditLog.id.asc()))
            rows: list[AuditLog] = result.scalars().all()

        # ----------------------------------------------------------------
        # Invariant: row count matches number of writes.
        # ----------------------------------------------------------------
        assert len(rows) == len(events), (
            f"Expected {len(events)} audit rows, found {len(rows)}"
        )

        for i, row in enumerate(rows):
            # Invariant c: every hash must be a 64-char lowercase hex string.
            assert _HEX_RE.match(row.hash), (
                f"Row {i} hash '{row.hash}' is not a valid 64-char hex string"
            )
            assert _HEX_RE.match(row.prev_hash) or row.prev_hash == GENESIS_HASH, (
                f"Row {i} prev_hash '{row.prev_hash}' is neither genesis nor a valid hash"
            )

            if i == 0:
                # Invariant a: the first row's prev_hash must be GENESIS_HASH.
                assert row.prev_hash == GENESIS_HASH, (
                    f"First row prev_hash '{row.prev_hash}' != GENESIS_HASH '{GENESIS_HASH}'"
                )
            else:
                # Invariant b: each row's prev_hash equals the preceding row's hash.
                assert row.prev_hash == rows[i - 1].hash, (
                    f"Row {i} prev_hash '{row.prev_hash}' "
                    f"!= row {i - 1} hash '{rows[i - 1].hash}'"
                )

    finally:
        async with engine.begin() as conn:
            await conn.run_sync(AuditLog.__table__.drop)
        await engine.dispose()


# ---------------------------------------------------------------------------
# Property 2: Hash chain integrity
# **Validates: Requirements 6.2, 6.3**
# ---------------------------------------------------------------------------


@given(events=_audit_sequence)
@settings(
    max_examples=50,
    suppress_health_check=[HealthCheck.too_slow],
)
def test_audit_hash_chain_integrity(events: list[dict]) -> None:
    """
    **Property 2: Hash chain integrity**
    **Validates: Requirements 6.2, 6.3**

    For N sequential audit writes the following must hold for all N rows:
      1. The first row's ``prev_hash`` equals GENESIS_HASH (``"0" * 64``).
      2. Each subsequent row's ``prev_hash`` equals the preceding row's ``hash``.
      3. Every ``hash`` is a 64-character lowercase hex string (SHA-256 output).

    Generates between 1 and 10 sequential audit events per example.
    """
    asyncio.run(_run_chain_test(events))
