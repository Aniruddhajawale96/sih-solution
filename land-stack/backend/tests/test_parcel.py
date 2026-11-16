"""
tests/test_parcel.py — Unit tests for routers/parcel.py.

Validates: Requirements 12.1, 12.2

Covers:
  - GET /parcels/{ulpin}  with a valid ULPIN → 200
  - GET /parcels/{ulpin}  with an unknown ULPIN → 404
  - CITIZEN caller receives ParcelPublic (no geometry field)
  - REV_OFF caller receives ParcelInternal (geometry + all fields)
  - POST /parcels by REV_OFF creates row and writes audit entry → 201
  - POST /parcels by CITIZEN → 403

Tests use httpx.AsyncClient with FastAPI's ASGI transport.
Dependency overrides replace get_db (AsyncSession mock) and get_redis (MagicMock).
No live PostgreSQL or Redis connection is required.
"""

from __future__ import annotations

import sys
import os

# Allow importing backend/ modules directly when running pytest from the repo root
_backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
import pytest_asyncio
import httpx

from core.auth import create_access_token

# ---------------------------------------------------------------------------
# JWT helpers — build tokens that satisfy get_current_user without Redis
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


# ---------------------------------------------------------------------------
# Minimal ORM-like stub for Parcel
# ---------------------------------------------------------------------------

class _FakeParcel:
    """Stand-in for the Parcel SQLAlchemy model returned from db.get / scalars."""

    def __init__(
        self,
        ulpin="MH-MUM-001",
        state_code="MH",
        district="Mumbai",
        tehsil="Andheri",
        village_or_city="Andheri East",
        area_sqm=250.0,
        survey_or_khasra_no="S/42",
        source_system="DILR",
        last_synced_at=None,
        geom=None,
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
        self.geom = geom


# ---------------------------------------------------------------------------
# AsyncSession mock factory
# ---------------------------------------------------------------------------

def _make_db_mock(parcel: "_FakeParcel | None" = None):
    """Return an AsyncMock that quacks like an AsyncSession for parcel queries."""
    db = AsyncMock()

    # db.get(Parcel, ulpin) — used by GET /{ulpin}
    db.get = AsyncMock(return_value=parcel)

    # db.execute(...) — used by check_jurisdiction (selects Parcel.state_code)
    # and by POST to check for duplicate ULPINs (also db.get)
    scalar_result = MagicMock()
    scalar_result.scalar_one_or_none.return_value = (
        parcel.state_code if parcel is not None else None
    )
    db.execute = AsyncMock(return_value=scalar_result)

    # flush / commit — called during POST
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.add = MagicMock()

    return db


def _make_redis_mock() -> AsyncMock:
    """Return a Redis mock where the token is NOT blacklisted."""
    redis_mock = AsyncMock()
    redis_mock.exists = AsyncMock(return_value=0)
    return redis_mock


# ---------------------------------------------------------------------------
# App + client fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture()
async def client_with_parcel(anyio_backend):
    """AsyncClient whose get_db returns a session holding one valid parcel."""
    from main import app
    from core.database import get_db
    from core.redis_client import get_redis

    parcel = _FakeParcel()
    db_mock = _make_db_mock(parcel)
    redis_mock = _make_redis_mock()

    app.dependency_overrides[get_db] = _make_db_override(db_mock)
    app.dependency_overrides[get_redis] = lambda: redis_mock

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac, parcel

    app.dependency_overrides.clear()


@pytest_asyncio.fixture()
async def client_no_parcel(anyio_backend):
    """AsyncClient whose get_db returns a session with NO parcel (simulate 404)."""
    from main import app
    from core.database import get_db
    from core.redis_client import get_redis

    db_mock = _make_db_mock(None)
    redis_mock = _make_redis_mock()

    app.dependency_overrides[get_db] = _make_db_override(db_mock)
    app.dependency_overrides[get_redis] = lambda: redis_mock

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests — GET /parcels/{ulpin}
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_get_parcel_valid_ulpin_returns_200(client_with_parcel):
    ac, parcel = client_with_parcel
    resp = await ac.get(
        f"/api/v1/parcels/{parcel.ulpin}",
        headers=_auth_headers("REV_OFF", jurisdiction="MH"),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["ulpin"] == parcel.ulpin


@pytest.mark.anyio
async def test_get_parcel_unknown_ulpin_returns_404(client_no_parcel):
    ac = client_no_parcel
    resp = await ac.get(
        "/api/v1/parcels/UNKNOWN-999",
        headers=_auth_headers("REV_OFF", jurisdiction="MH"),
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Tests — CITIZEN gets ParcelPublic (no geometry)
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_citizen_receives_parcel_public_no_geom(client_with_parcel):
    ac, parcel = client_with_parcel
    resp = await ac.get(
        f"/api/v1/parcels/{parcel.ulpin}",
        headers=_auth_headers("CITIZEN"),
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    # ParcelPublic fields present
    assert data["ulpin"] == parcel.ulpin
    assert data["district"] == parcel.district
    assert data["area_sqm"] == parcel.area_sqm
    # 'geom' must NOT be present in the citizen view
    assert "geom" not in data


# ---------------------------------------------------------------------------
# Tests — Officer gets ParcelInternal (geometry field present, even if None)
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_officer_receives_parcel_internal_with_geom_key(client_with_parcel):
    ac, parcel = client_with_parcel
    resp = await ac.get(
        f"/api/v1/parcels/{parcel.ulpin}",
        headers=_auth_headers("REV_OFF", jurisdiction="MH"),
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    # ParcelInternal includes source_system (not in PublicSchema)
    assert "source_system" in data
    # geom key is present in the internal view (may be None if no geometry in fixture)
    assert "geom" in data


# ---------------------------------------------------------------------------
# Tests — POST /parcels
# ---------------------------------------------------------------------------

_GEOJSON = json.dumps(
    {
        "type": "Polygon",
        "coordinates": [
            [[72.8, 19.0], [72.9, 19.0], [72.9, 19.1], [72.8, 19.1], [72.8, 19.0]]
        ],
    }
)

_PARCEL_PAYLOAD = {
    "ulpin": "MH-MUM-NEW-001",
    "state_code": "MH",
    "district": "Mumbai",
    "tehsil": "Andheri",
    "village_or_city": "Andheri West",
    "area_sqm": 150.0,
    "survey_or_khasra_no": "S/99",
    "source_system": "DILR",
    "geom": _GEOJSON,
}


@pytest_asyncio.fixture()
async def client_for_post(anyio_backend):
    """
    AsyncClient wired for POST /parcels tests.

    db.get returns None (no duplicate) on the first call, then the newly
    created parcel after db.refresh. write_audit is patched to avoid a live DB
    call for the audit chain query.
    """
    from main import app
    from core.database import get_db
    from core.redis_client import get_redis

    new_parcel = _FakeParcel(
        ulpin="MH-MUM-NEW-001",
        state_code="MH",
        district="Mumbai",
    )

    db_mock = AsyncMock()
    db_mock.get = AsyncMock(return_value=None)  # no duplicate

    # db.execute used by write_audit to fetch last hash
    scalar_result = MagicMock()
    scalar_result.scalar_one_or_none.return_value = None  # genesis hash path
    db_mock.execute = AsyncMock(return_value=scalar_result)

    db_mock.flush = AsyncMock()
    db_mock.commit = AsyncMock()
    db_mock.add = MagicMock()

    # After db.refresh the parcel attributes should be readable
    async def _fake_refresh(obj):
        # populate the passed-in Parcel instance with fixture values
        for attr, val in vars(new_parcel).items():
            setattr(obj, attr, val)

    db_mock.refresh = AsyncMock(side_effect=_fake_refresh)

    redis_mock = _make_redis_mock()

    app.dependency_overrides[get_db] = _make_db_override(db_mock)
    app.dependency_overrides[get_redis] = lambda: redis_mock

    yield app, db_mock, redis_mock

    app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_post_parcel_by_rev_off_creates_row_and_audit(client_for_post):
    app, db_mock, _ = client_for_post

    with patch("routers.parcel.write_audit", new_callable=AsyncMock) as mock_audit, \
         patch("routers.parcel.ST_GeomFromGeoJSON", return_value="<geom_expr>"):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as ac:
            resp = await ac.post(
                "/api/v1/parcels",
                json=_PARCEL_PAYLOAD,
                headers=_auth_headers("REV_OFF"),
            )

    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["success"] is True

    # Parcel row was added to the session
    db_mock.add.assert_called_once()
    db_mock.commit.assert_called_once()

    # Audit entry was written
    mock_audit.assert_called_once()
    _, audit_kwargs = mock_audit.call_args
    assert audit_kwargs.get("action") == "CREATE_PARCEL"
    assert audit_kwargs.get("resource_type") == "parcel"
    assert audit_kwargs.get("resource_id") == _PARCEL_PAYLOAD["ulpin"]


@pytest.mark.anyio
async def test_post_parcel_by_citizen_returns_403(anyio_backend):
    from main import app
    from core.database import get_db
    from core.redis_client import get_redis

    db_mock = AsyncMock()
    redis_mock = _make_redis_mock()

    app.dependency_overrides[get_db] = _make_db_override(db_mock)
    app.dependency_overrides[get_redis] = lambda: redis_mock

    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as ac:
            resp = await ac.post(
                "/api/v1/parcels",
                json=_PARCEL_PAYLOAD,
                headers=_auth_headers("CITIZEN"),
            )
        assert resp.status_code == 403
    finally:
        app.dependency_overrides.clear()
