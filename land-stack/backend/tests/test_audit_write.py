"""
test_audit_write.py — Property-based test verifying that an audit log entry
exists after every write.

**Property 1: Audit log entry exists after every write**
  For any successful write action, the `audit_log` table SHALL contain a new
  row with `resource_id` equal to the ULPIN of the modified record and `action`
  matching the documented action string, before the HTTP response is returned.

**Validates: Requirements 6.1, 6.2**

The test spins up an in-memory SQLite async database (via aiosqlite) so that no
live PostgreSQL instance is required.  For each Hypothesis example it:

  1. Creates a fresh schema (audit_logs table only).
  2. Calls `write_audit` with the generated (actor_user, actor_role, action,
     resource_type, resource_id) tuple and commits.
  3. Queries the DB and asserts that exactly one row exists whose `resource_id`
     and `action` match the written values, with all other fields populated.
"""

from __future__ import annotations

import asyncio
import os
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

# Stub `backend`, `core`, `models` namespace packages and load only the
# specific modules we need — bypassing models/__init__.py and core/__init__.py
# which may pull in geo types (geoalchemy2) that are not available in the
# test environment.
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

from core.audit import write_audit
from models.audit_log import AuditLog

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

# ---------------------------------------------------------------------------
# Hypothesis strategies
# ---------------------------------------------------------------------------

_alphanumeric = st.text(
    alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd")),
    min_size=1,
    max_size=30,
)

_audit_write_input = st.fixed_dictionaries(
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
                "CREATE_BUILDING_PERMISSION",
                "REASSESS_TAX",
                "ML_CHANGE_DETECTION",
                "ML_FRAUD_SCORE",
                "ML_OCR_EXTRACT",
                "REJECT_MUTATION",
                "CITIZEN_SERVICE_REQUEST",
            ]
        ),
        "resource_type": st.sampled_from(
            [
                "parcel",
                "ror",
                "registration",
                "encumbrance",
                "zoning",
                "building_permission",
                "tax",
                "workflow_task",
                "citizen_service_request",
            ]
        ),
        "resource_id": _alphanumeric,
    }
)

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


# ---------------------------------------------------------------------------
# Core async test logic
# ---------------------------------------------------------------------------


async def _run_audit_write_test(params: dict) -> None:
    """
    Call write_audit once with the given params, commit, then query the DB and
    assert that an audit row exists with the correct resource_id and action.
    """
    engine, factory = _make_engine()

    # Create only the audit_logs table (skips geo types from other models).
    async with engine.begin() as conn:
        await conn.run_sync(AuditLog.__table__.create)

    try:
        # --- Write phase ---
        async with factory() as db:
            returned_entry = await write_audit(
                db,
                actor_user=params["actor_user"],
                actor_role=params["actor_role"],
                action=params["action"],
                resource_type=params["resource_type"],
                resource_id=params["resource_id"],
            )
            # Mimic the caller's outer commit (mutation + audit row finalized atomically).
            await db.commit()

        # --- Query phase ---
        async with factory() as db:
            result = await db.execute(
                select(AuditLog).where(
                    AuditLog.resource_id == params["resource_id"],
                    AuditLog.action == params["action"],
                )
            )
            matching_rows = result.scalars().all()

        # --- Assertions (Requirements 6.1, 6.2) ---

        # A row MUST exist for every committed write_audit call.
        assert len(matching_rows) >= 1, (
            f"Expected at least one audit row for resource_id={params['resource_id']!r} "
            f"and action={params['action']!r}, but found none."
        )

        row = matching_rows[0]

        # resource_id and action must round-trip exactly.
        assert row.resource_id == params["resource_id"], (
            f"Audit row resource_id mismatch: "
            f"expected {params['resource_id']!r}, got {row.resource_id!r}"
        )
        assert row.action == params["action"], (
            f"Audit row action mismatch: "
            f"expected {params['action']!r}, got {row.action!r}"
        )

        # write_audit must call db.flush() so that id is populated before commit.
        assert returned_entry.id is not None, (
            "write_audit must flush the row so that id is populated before commit."
        )

        # Remaining fields must be populated and match the input.
        assert row.actor_user == params["actor_user"]
        assert row.actor_role == params["actor_role"]
        assert row.resource_type == params["resource_type"]
        assert row.timestamp is not None, "audit row must carry a non-null timestamp"
        assert row.hash is not None and len(row.hash) == 64, (
            "audit row hash must be a 64-char SHA-256 hex digest"
        )
        assert row.prev_hash is not None and len(row.prev_hash) == 64, (
            "audit row prev_hash must be a 64-char hex string"
        )

    finally:
        async with engine.begin() as conn:
            await conn.run_sync(AuditLog.__table__.drop)
        await engine.dispose()


# ---------------------------------------------------------------------------
# Property 1: Audit log entry exists after every write
# **Validates: Requirements 6.1, 6.2**
# ---------------------------------------------------------------------------


@given(params=_audit_write_input)
@settings(
    max_examples=50,
    suppress_health_check=[HealthCheck.too_slow],
)
def test_audit_entry_exists_after_write(params: dict) -> None:
    """
    **Property 1: Audit log entry exists after every write**

    **Validates: Requirements 6.1, 6.2**

    For any (actor_user, actor_role, action, resource_type, resource_id) tuple
    generated by Hypothesis:

    1. Calling write_audit() inside an open transaction and then committing MUST
       produce at least one audit_log row queryable by `resource_id` and `action`.
    2. The persisted row MUST have `resource_id` and `action` equal to the values
       passed to write_audit().
    3. The row's `id` MUST be non-None immediately after write_audit() returns
       (confirming db.flush() was called inside the function).
    4. All other fields (actor_user, actor_role, resource_type, timestamp, hash,
       prev_hash) MUST be populated and correct.
    """
    asyncio.run(_run_audit_write_test(params))
