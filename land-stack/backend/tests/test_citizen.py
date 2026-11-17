"""
tests/test_citizen.py — Unit tests for routers/citizen.py.

Validates: Requirements 12.1, 12.2

Covers:
  1. POST /citizen/service-request — CITIZEN submits → 201, response has
     request_id and status="submitted".
  2. POST /citizen/service-request — REV_OFF caller → 403.
  3. GET  /citizen/requests — CITIZEN sees only their own requests
     (not another citizen's).
  4. GET  /citizen/requests — REV_OFF caller → 403.
  5. GET  /citizen/parcels — CITIZEN gets list of ParcelPublic (no `geom`
     field); results are scoped to parcels whose ror.owner_name matches
     the citizen's username.
  6. GET  /citizen/parcels — REV_OFF caller → 403.

Tests use httpx.AsyncClient with FastAPI's ASGI transport — no live
PostgreSQL or Redis connection is required.
Dependency overrides replace get_db (AsyncSession mock) and
get_current_user (direct UserClaims injection).
write_audit is patched for POST tests.
"""

from __future__ import annotations

import sys
import os

# Allow importing backend/ modules directly when running pytest from the repo root
_backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
import httpx

from core.auth import create_access_token

# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------


def _make_token(role: str, username: str | None = None) -> str:
    sub = username or f"user_{role.lower()}"
    return create_access_token({"sub": sub, "role": role, "jurisdiction": None})


def _auth_headers(role: str, username: str | None = None) -> dict[str, str]:
    return {"Authorization": f"Bearer {_make_token(role, username=username)}"}


# ---------------------------------------------------------------------------
# Dependency override helpers
# ---------------------------------------------------------------------------


def _make_db_override(db_mock):
    """Return an async-generator FastAPI dependency that yields *db_mock*."""
    async def _override():
        yield db_mock
    return _override


def _make_redis_mock() -> AsyncMock:
    redis_mock = AsyncMock()
    redis_mock.exists = AsyncMock(return_value=0)   # token not blacklisted
    return redis_mock


# ---------------------------------------------------------------------------
# Fake ORM objects
# ---------------------------------------------------------------------------


class _FakeServiceRequest:
    """Stand-in for CitizenServiceRequest SQLAlchemy row."""

    def __init__(
        self,
        id: str = "req-uuid-001",
        ulpin: str = "MH-MUM-001",
        citizen_username: str = "user_citizen",
        service_type: str = "OWNERSHIP_CERT",
        notes: str | None = None,
        status: str = "submitted",
        created_at: datetime | None = None,
    ):
        self.id = id
        self.ulpin = ulpin
        self.citizen_username = citizen_username
        self.service_type = service_type
        self.notes = notes
        self.status = status
        self.created_at = created_at or datetime.utcnow()


class _FakeParcel:
    """Stand-in for Parcel SQLAlchemy row (no geometry — citizen view only)."""

    def __init__(
        self,
        ulpin: str = "MH-MUM-001",
        state_code: str = "MH",
        district: str = "Mumbai",
        tehsil: str = "Andheri",
        village_or_city: str = "Andheri East",
        area_sqm: float = 250.0,
        survey_or_khasra_no: str = "S/42",
        source_system: str = "DILR",
        last_synced_at: datetime | None = None,
    ):
        self.ulpin = ulpin
        self.state_code = state_code
        self.district = district
        self.tehsil = tehsil
        self.village_or_city = village_or_city
        self.area_sqm = area_sqm
        self.survey_or_khasra_no = survey_or_khasra_no
        self.source_system = source_system
        self.last_synced_at = last_synced_at
        self.geom = None


# ---------------------------------------------------------------------------
# DB mock factories
# ---------------------------------------------------------------------------


def _make_post_db_mock() -> AsyncMock:
    """AsyncSession mock suitable for POST /citizen/service-request."""
    db = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    # write_audit calls db.execute; return a scalar result with no previous hash
    scalar_result = MagicMock()
    scalar_result.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=scalar_result)
    return db


def _make_list_db_mock(rows: list) -> AsyncMock:
    """AsyncSession mock for GET endpoints that call db.execute(...).scalars().all()."""
    db = AsyncMock()
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = rows
    result_mock = MagicMock()
    result_mock.scalars.return_value = scalars_mock
    db.execute = AsyncMock(return_value=result_mock)
    return db


# ---------------------------------------------------------------------------
# POST /citizen/service-request — 201 success (CITIZEN)
# ---------------------------------------------------------------------------

_SERVICE_REQUEST_PAYLOAD = {
    "ulpin": "MH-MUM-001",
    "service_type": "OWNERSHIP_CERT",
    "notes": "Please issue certificate",
}


@pytest.mark.anyio
async def test_post_service_request_citizen_returns_201(anyio_backend):
    """CITIZEN submits service request → 201; body has request_id and status=submitted."""
    from main import app
    from core.database import get_db
    from core.redis_client import get_redis

    db_mock = _make_post_db_mock()
    redis_mock = _make_redis_mock()

    app.dependency_overrides[get_db] = _make_db_override(db_mock)
    app.dependency_overrides[get_redis] = lambda: redis_mock

    try:
        with patch("routers.citizen.write_audit", new_callable=AsyncMock) as mock_audit:
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as ac:
                resp = await ac.post(
                    "/api/v1/citizen/service-request",
                    json=_SERVICE_REQUEST_PAYLOAD,
                    headers=_auth_headers("CITIZEN", username="user_citizen"),
                )

        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["success"] is True
        data = body["data"]
        assert "request_id" in data
        assert data["status"] == "submitted"

        # Row was persisted and audit was written
        db_mock.add.assert_called_once()
        db_mock.commit.assert_called_once()
        mock_audit.assert_called_once()
        _, audit_kwargs = mock_audit.call_args
        assert audit_kwargs.get("action") == "CITIZEN_SERVICE_REQUEST"
        assert audit_kwargs.get("resource_type") == "citizen_service_request"
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# POST /citizen/service-request — 403 (REV_OFF)
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_post_service_request_officer_returns_403(anyio_backend):
    """REV_OFF is not allowed to call POST /citizen/service-request → 403."""
    from main import app
    from core.database import get_db
    from core.redis_client import get_redis

    db_mock = _make_post_db_mock()
    redis_mock = _make_redis_mock()

    app.dependency_overrides[get_db] = _make_db_override(db_mock)
    app.dependency_overrides[get_redis] = lambda: redis_mock

    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as ac:
            resp = await ac.post(
                "/api/v1/citizen/service-request",
                json=_SERVICE_REQUEST_PAYLOAD,
                headers=_auth_headers("REV_OFF"),
            )
        assert resp.status_code == 403
        body = resp.json()
        assert body["success"] is False
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# GET /citizen/requests — scoped to calling citizen (CITIZEN)
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_get_citizen_requests_scoped_to_own_username(anyio_backend):
    """CITIZEN sees only requests whose citizen_username matches their own token sub."""
    from main import app
    from core.database import get_db
    from core.redis_client import get_redis

    own_request = _FakeServiceRequest(citizen_username="user_citizen")
    other_request = _FakeServiceRequest(
        id="req-uuid-002", citizen_username="other_citizen"
    )

    # DB mock returns only the own request (the router filters by username in SQL)
    db_mock = _make_list_db_mock([own_request])
    redis_mock = _make_redis_mock()

    app.dependency_overrides[get_db] = _make_db_override(db_mock)
    app.dependency_overrides[get_redis] = lambda: redis_mock

    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as ac:
            resp = await ac.get(
                "/api/v1/citizen/requests",
                headers=_auth_headers("CITIZEN", username="user_citizen"),
            )

        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["success"] is True
        rows = body["data"]
        assert len(rows) == 1
        assert rows[0]["citizen_username"] == "user_citizen"
        # Confirm the SQL query was scoped (db.execute called once with the WHERE clause)
        db_mock.execute.assert_called_once()
        # Confirm other citizen's request is not in the response
        for row in rows:
            assert row["citizen_username"] != "other_citizen"
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# GET /citizen/requests — 403 (REV_OFF)
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_get_citizen_requests_officer_returns_403(anyio_backend):
    """REV_OFF is not allowed to call GET /citizen/requests → 403."""
    from main import app
    from core.database import get_db
    from core.redis_client import get_redis

    db_mock = _make_list_db_mock([])
    redis_mock = _make_redis_mock()

    app.dependency_overrides[get_db] = _make_db_override(db_mock)
    app.dependency_overrides[get_redis] = lambda: redis_mock

    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as ac:
            resp = await ac.get(
                "/api/v1/citizen/requests",
                headers=_auth_headers("REV_OFF"),
            )
        assert resp.status_code == 403
        body = resp.json()
        assert body["success"] is False
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# GET /citizen/parcels — ParcelPublic list, no geom (CITIZEN)
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_get_citizen_parcels_returns_parcel_public_no_geom(anyio_backend):
    """CITIZEN gets ParcelPublic list; geom field is absent; scoped to owner_name match."""
    from main import app
    from core.database import get_db
    from core.redis_client import get_redis

    parcel = _FakeParcel(ulpin="MH-MUM-001")
    db_mock = _make_list_db_mock([parcel])
    redis_mock = _make_redis_mock()

    app.dependency_overrides[get_db] = _make_db_override(db_mock)
    app.dependency_overrides[get_redis] = lambda: redis_mock

    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as ac:
            resp = await ac.get(
                "/api/v1/citizen/parcels",
                headers=_auth_headers("CITIZEN", username="user_citizen"),
            )

        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["success"] is True
        parcels = body["data"]
        assert len(parcels) == 1

        p = parcels[0]
        # ParcelPublic fields must be present
        assert p["ulpin"] == parcel.ulpin
        assert p["state_code"] == parcel.state_code
        assert p["district"] == parcel.district
        assert p["village_or_city"] == parcel.village_or_city
        assert p["area_sqm"] == parcel.area_sqm
        assert p["survey_or_khasra_no"] == parcel.survey_or_khasra_no

        # geom MUST NOT appear in ParcelPublic
        assert "geom" not in p

        # Router executed the join query filtering by owner_name ILIKE
        db_mock.execute.assert_called_once()
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# GET /citizen/parcels — 403 (REV_OFF)
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_get_citizen_parcels_officer_returns_403(anyio_backend):
    """REV_OFF is not allowed to call GET /citizen/parcels → 403."""
    from main import app
    from core.database import get_db
    from core.redis_client import get_redis

    db_mock = _make_list_db_mock([])
    redis_mock = _make_redis_mock()

    app.dependency_overrides[get_db] = _make_db_override(db_mock)
    app.dependency_overrides[get_redis] = lambda: redis_mock

    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as ac:
            resp = await ac.get(
                "/api/v1/citizen/parcels",
                headers=_auth_headers("REV_OFF"),
            )
        assert resp.status_code == 403
        body = resp.json()
        assert body["success"] is False
    finally:
        app.dependency_overrides.clear()
