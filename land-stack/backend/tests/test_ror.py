"""
tests/test_ror.py — Unit tests for routers/ror.py.

Validates: Requirements 12.1, 12.2

Covers:
  - GET /ror/{ulpin}  with a valid ULPIN → 200
  - GET /ror/{ulpin}  with an unknown ULPIN → 404
  - CITIZEN caller receives RorPublic (owner_name masked)
  - REV_OFF caller receives RorInternal (owner_name unmasked)
  - PUT /ror/{ulpin} by REV_OFF updates row and writes audit → 200
  - PUT /ror/{ulpin} with jurisdiction mismatch → 403

Tests use httpx.AsyncClient with FastAPI's ASGI transport.
Dependency overrides replace get_db (AsyncSession mock) and get_redis (MagicMock).
No live PostgreSQL or Redis connection is required.
"""

from __future__ import annotations

import sys
import os

_backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
import pytest_asyncio
import httpx

from core.auth import create_access_token

# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------

def _make_token(role: str, jurisdiction: str | None = None) -> str:
    return create_access_token(
        {"sub": f"user_{role.lower()}", "role": role, "jurisdiction": jurisdiction}
    )


def _auth_headers(role: str, jurisdiction: str | None = None) -> dict[str, str]:
    return {"Authorization": f"Bearer {_make_token(role, jurisdiction)}"}


# ---------------------------------------------------------------------------
# Dependency override helpers
# ---------------------------------------------------------------------------

def _make_db_override(db_mock):
    """Create an async-generator FastAPI dependency override for get_db.

    FastAPI detects async-generator functions via ``inspect.isasyncgenfunction``,
    so we must return an actual ``async def`` with ``yield`` — not a lambda
    wrapping a generator.
    """
    async def _override():
        yield db_mock
    return _override


def _make_redis_mock() -> AsyncMock:
    """Return a Redis mock where the token is NOT blacklisted."""
    redis_mock = AsyncMock()
    redis_mock.exists = AsyncMock(return_value=0)
    redis_mock.publish = AsyncMock(return_value=1)
    return redis_mock


# ---------------------------------------------------------------------------
# Minimal ORM-like stub for Ror
# ---------------------------------------------------------------------------

class _FakeRor:
    def __init__(
        self,
        ulpin="MH-MUM-001",
        owner_name="Ramesh Kumar",
        tenure_type="Freehold",
        khatauni_no="K/42",
        land_use_type="Residential",
        mutation_status="Clear",
        last_updated: date | None = None,
    ):
        self.ulpin = ulpin
        self.owner_name = owner_name
        self.tenure_type = tenure_type
        self.khatauni_no = khatauni_no
        self.land_use_type = land_use_type
        self.mutation_status = mutation_status
        self.last_updated = last_updated or date(2024, 1, 15)


# ---------------------------------------------------------------------------
# AsyncSession mock factories
# ---------------------------------------------------------------------------

def _make_ror_db_mock(ror: "_FakeRor | None", parcel_state_code: str | None = "MH"):
    """
    Build a mock AsyncSession for RoR tests.

    db.execute is called in two places:
      1. check_jurisdiction — SELECT Parcel.state_code WHERE ulpin = ?
      2. get_ror / update_ror — SELECT Ror WHERE ulpin = ?

    We distinguish the two by inspecting whether the query string references
    'parcels' or 'ror', but since we receive SQLAlchemy Select objects (not
    strings) we simply rotate between two pre-canned results using a call counter.
    """
    db = AsyncMock()

    call_count: list[int] = [0]

    async def _execute(stmt, *args, **kwargs):
        call_count[0] += 1
        result = MagicMock()
        # check_jurisdiction always queries parcels first on PUT; GET routes
        # don't call check_jurisdiction so order doesn't matter there.
        # We use the call index to decide which result to return.
        if call_count[0] == 1:
            # First execute: could be check_jurisdiction (parcels) or ror SELECT
            # For GET routes there's only one execute (the ror SELECT).
            # For PUT routes the first execute comes from check_jurisdiction.
            # We'll always return a "ror" result for index 1; check_jurisdiction
            # gets its own path via the parcel fixture (see below).
            result.scalar_one_or_none.return_value = ror
        else:
            result.scalar_one_or_none.return_value = ror
        return result

    db.execute = AsyncMock(side_effect=_execute)
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.add = MagicMock()

    return db


def _make_jurisdiction_db_mock(
    ror: "_FakeRor | None",
    parcel_state_code: str | None,
):
    """
    Mock AsyncSession for PUT /ror tests where check_jurisdiction fires first.

    check_jurisdiction calls db.execute(SELECT Parcel.state_code ...) and
    the router calls db.execute(SELECT Ror ...) second. We serve the two
    results in order.
    """
    db = AsyncMock()

    call_count: list[int] = [0]

    async def _execute(stmt, *args, **kwargs):
        call_count[0] += 1
        result = MagicMock()
        if call_count[0] == 1:
            # First call: check_jurisdiction → Parcel.state_code
            result.scalar_one_or_none.return_value = parcel_state_code
        else:
            # Second call: ror SELECT
            result.scalar_one_or_none.return_value = ror
        return result

    db.execute = AsyncMock(side_effect=_execute)
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.add = MagicMock()

    return db


# ---------------------------------------------------------------------------
# App + client fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture()
async def client_with_ror(anyio_backend):
    from main import app
    from core.database import get_db
    from core.redis_client import get_redis

    ror = _FakeRor()
    db_mock = _make_ror_db_mock(ror)
    redis_mock = _make_redis_mock()

    app.dependency_overrides[get_db] = _make_db_override(db_mock)
    app.dependency_overrides[get_redis] = lambda: redis_mock

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac, ror

    app.dependency_overrides.clear()


@pytest_asyncio.fixture()
async def client_no_ror(anyio_backend):
    from main import app
    from core.database import get_db
    from core.redis_client import get_redis

    db_mock = _make_ror_db_mock(None)
    redis_mock = _make_redis_mock()

    app.dependency_overrides[get_db] = _make_db_override(db_mock)
    app.dependency_overrides[get_redis] = lambda: redis_mock

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests — GET /ror/{ulpin}
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_get_ror_valid_ulpin_returns_200(client_with_ror):
    ac, ror = client_with_ror
    resp = await ac.get(
        f"/api/v1/ror/{ror.ulpin}",
        headers=_auth_headers("REV_OFF", jurisdiction="MH"),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["ulpin"] == ror.ulpin


@pytest.mark.anyio
async def test_get_ror_unknown_ulpin_returns_not_found(client_no_ror):
    ac = client_no_ror
    resp = await ac.get(
        "/api/v1/ror/UNKNOWN-999",
        headers=_auth_headers("REV_OFF", jurisdiction="MH"),
    )
    assert resp.status_code == 200  # envelope wraps the error (not HTTP 404)
    body = resp.json()
    assert body["success"] is False
    assert any(e["code"] == "NOT_FOUND" for e in body["errors"])


# ---------------------------------------------------------------------------
# Tests — CITIZEN receives masked owner_name
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_citizen_receives_ror_public_masked_owner(client_with_ror):
    ac, ror = client_with_ror
    resp = await ac.get(
        f"/api/v1/ror/{ror.ulpin}",
        headers=_auth_headers("CITIZEN"),
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    # owner_name must be masked (contains ***)
    assert "***" in data["owner_name"]
    # original unmasked name must NOT be present in full
    assert ror.owner_name not in data["owner_name"]


# ---------------------------------------------------------------------------
# Tests — REV_OFF receives unmasked owner_name
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_officer_receives_ror_internal_unmasked_owner(client_with_ror):
    ac, ror = client_with_ror
    resp = await ac.get(
        f"/api/v1/ror/{ror.ulpin}",
        headers=_auth_headers("REV_OFF", jurisdiction="MH"),
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["owner_name"] == ror.owner_name


# ---------------------------------------------------------------------------
# Tests — PUT /ror/{ulpin} by REV_OFF updates row and writes audit
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_put_ror_by_rev_off_updates_and_writes_audit(anyio_backend):
    from main import app
    from core.database import get_db
    from core.redis_client import get_redis

    ror = _FakeRor()
    db_mock = _make_jurisdiction_db_mock(ror, parcel_state_code="MH")
    redis_mock = _make_redis_mock()

    app.dependency_overrides[get_db] = _make_db_override(db_mock)
    app.dependency_overrides[get_redis] = lambda: redis_mock

    try:
        with patch("routers.ror.write_audit", new_callable=AsyncMock) as mock_audit:
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as ac:
                resp = await ac.put(
                    f"/api/v1/ror/{ror.ulpin}",
                    json={"mutation_status": "Pending"},
                    headers=_auth_headers("REV_OFF", jurisdiction="MH"),
                )

        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["success"] is True

        # The updated mutation_status is reflected in the response
        assert body["data"]["mutation_status"] == "Pending"

        # Audit entry was written
        mock_audit.assert_called_once()
        _, audit_kwargs = mock_audit.call_args
        assert audit_kwargs.get("action") == "UPDATE_ROR"
        assert audit_kwargs.get("resource_type") == "ror"
        assert audit_kwargs.get("resource_id") == ror.ulpin

        # DB commit was called
        db_mock.commit.assert_called_once()
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests — PUT /ror/{ulpin} jurisdiction mismatch → 403
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_put_ror_jurisdiction_mismatch_returns_403(anyio_backend):
    """
    REV_OFF whose jurisdiction is 'TN' tries to update a parcel in state 'MH'.
    check_jurisdiction must reject with 403.
    """
    from main import app
    from core.database import get_db
    from core.redis_client import get_redis

    ror = _FakeRor()
    # parcel.state_code is "MH" but the token claims jurisdiction "TN"
    db_mock = _make_jurisdiction_db_mock(ror, parcel_state_code="MH")
    redis_mock = _make_redis_mock()

    app.dependency_overrides[get_db] = _make_db_override(db_mock)
    app.dependency_overrides[get_redis] = lambda: redis_mock

    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as ac:
            resp = await ac.put(
                f"/api/v1/ror/{ror.ulpin}",
                json={"mutation_status": "Pending"},
                headers=_auth_headers("REV_OFF", jurisdiction="TN"),  # wrong jurisdiction
            )

        assert resp.status_code == 403
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests — PUT /ror/{ulpin} by NATL_ADMIN bypasses jurisdiction check
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_put_ror_by_natl_admin_bypasses_jurisdiction(anyio_backend):
    """NATL_ADMIN has global access — no jurisdiction check is enforced."""
    from main import app
    from core.database import get_db
    from core.redis_client import get_redis

    ror = _FakeRor()
    # For NATL_ADMIN check_jurisdiction returns immediately without DB call,
    # so only the ror SELECT fires (call_count=1 → ror).
    db_mock = _make_ror_db_mock(ror)
    redis_mock = _make_redis_mock()

    app.dependency_overrides[get_db] = _make_db_override(db_mock)
    app.dependency_overrides[get_redis] = lambda: redis_mock

    try:
        with patch("routers.ror.write_audit", new_callable=AsyncMock):
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as ac:
                resp = await ac.put(
                    f"/api/v1/ror/{ror.ulpin}",
                    json={"owner_name": "Updated Name"},
                    headers=_auth_headers("NATL_ADMIN"),  # jurisdiction=None
                )

        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
    finally:
        app.dependency_overrides.clear()
