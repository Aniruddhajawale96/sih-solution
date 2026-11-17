"""
tests/test_admin.py — Unit tests for routers/admin.py.

Validates: Requirements 12.1, 12.2

Covers:
  GET  /admin/state-adapter/{state_code}
    - STATE_ADMIN (own state) → 200 with config list
    - STATE_ADMIN (different state) → 403
    - NATL_ADMIN → 200 with config list
    - CITIZEN → 403

  PUT  /admin/state-adapter/{state_code}
    - NATL_ADMIN → 200, config updated, audit UPDATE_STATE_ADAPTER written
    - STATE_ADMIN → 403 (not allowed)
    - 404 when no config rows exist for the state

  GET  /admin/users
    - NATL_ADMIN → 200, all users, no hashed_password in output
    - STATE_ADMIN → 200, scoped to own jurisdiction
    - CITIZEN → 403

Tests use httpx.AsyncClient with FastAPI's ASGI transport.
Dependency overrides replace get_current_user, get_db, and get_redis.
No live PostgreSQL or Redis connection is required.
"""

from __future__ import annotations

import sys
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import httpx
from fastapi import status

# Allow importing backend/ modules directly when running pytest from the repo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from main import app
from core.rbac import UserClaims, get_current_user
from core.database import get_db
from core.redis_client import get_redis
from models.state_adapter import StateAdapterConfig
from models.users import User


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _make_user_claims(
    role: str,
    username: str = "testuser",
    jurisdiction: str | None = None,
) -> UserClaims:
    """Build a UserClaims dataclass for dependency override."""
    return UserClaims(username=username, role=role, jurisdiction=jurisdiction)


class _FakeConfig:
    """Minimal stand-in for a StateAdapterConfig ORM row."""

    def __init__(
        self,
        id: int = 1,
        state_code: str = "PB",
        source_field_name: str = "village_name",
        canonical_field_name: str = "village_or_city",
        unit_conversion_factor: float = 1.0,
        language_code: str = "en",
    ):
        self.id = id
        self.state_code = state_code
        self.source_field_name = source_field_name
        self.canonical_field_name = canonical_field_name
        self.unit_conversion_factor = unit_conversion_factor
        self.language_code = language_code


class _FakeUser:
    """Minimal stand-in for a User ORM row."""

    def __init__(
        self,
        username: str = "admin1",
        hashed_password: str = "$2b$12$secret_hashed_value_here",
        role: str = "STATE_ADMIN",
        jurisdiction: str | None = "PB",
        is_active: bool = True,
    ):
        self.username = username
        self.hashed_password = hashed_password
        self.role = role
        self.jurisdiction = jurisdiction
        self.is_active = is_active


def _make_db_with_configs(configs: list[_FakeConfig]):
    """Return an AsyncMock session whose execute().scalars().all() returns *configs*."""
    db = AsyncMock()
    scalars_mock = MagicMock()
    scalars_mock.all = MagicMock(return_value=configs)
    exec_result = MagicMock()
    exec_result.scalars = MagicMock(return_value=scalars_mock)
    db.execute = AsyncMock(return_value=exec_result)
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    return db


def _make_db_with_users(users: list[_FakeUser]):
    """Return an AsyncMock session whose execute().scalars().all() returns *users*."""
    db = AsyncMock()
    scalars_mock = MagicMock()
    scalars_mock.all = MagicMock(return_value=users)
    exec_result = MagicMock()
    exec_result.scalars = MagicMock(return_value=scalars_mock)
    db.execute = AsyncMock(return_value=exec_result)
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    return db


def _override_deps(db, user_claims):
    """Wire dependency overrides for db, redis, and current user."""
    async def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_redis] = lambda: AsyncMock()
    app.dependency_overrides[get_current_user] = lambda: user_claims


def _clear_overrides():
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# GET /admin/state-adapter/{state_code}
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_get_state_adapter_state_admin_own_state_returns_200():
    """STATE_ADMIN requesting own state's adapter config → 200 with list."""
    configs = [
        _FakeConfig(id=1, state_code="PB", source_field_name="village_name",
                    canonical_field_name="village_or_city", unit_conversion_factor=1.0),
        _FakeConfig(id=2, state_code="PB", source_field_name="area_acres",
                    canonical_field_name="area_sqm", unit_conversion_factor=4046.86),
    ]
    db = _make_db_with_configs(configs)
    user = _make_user_claims("STATE_ADMIN", "state_admin", "PB")

    _override_deps(db, user)
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/v1/admin/state-adapter/PB")
    finally:
        _clear_overrides()

    assert resp.status_code == status.HTTP_200_OK, resp.text
    body = resp.json()
    assert body["success"] is True
    data = body["data"]
    assert isinstance(data, list)
    assert len(data) == 2
    assert data[0]["state_code"] == "PB"
    assert data[0]["source_field_name"] == "village_name"
    assert data[1]["unit_conversion_factor"] == 4046.86


@pytest.mark.anyio
async def test_get_state_adapter_state_admin_different_state_returns_403():
    """STATE_ADMIN requesting a different state's adapter config → 403."""
    configs = [_FakeConfig(id=1, state_code="TN")]
    db = _make_db_with_configs(configs)
    user = _make_user_claims("STATE_ADMIN", "state_admin", "PB")

    _override_deps(db, user)
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/v1/admin/state-adapter/TN")
    finally:
        _clear_overrides()

    assert resp.status_code == status.HTTP_403_FORBIDDEN
    body = resp.json()
    assert body["success"] is False


@pytest.mark.anyio
async def test_get_state_adapter_natl_admin_returns_200():
    """NATL_ADMIN can retrieve adapter config for any state → 200."""
    configs = [_FakeConfig(id=1, state_code="TN", source_field_name="area_acres")]
    db = _make_db_with_configs(configs)
    user = _make_user_claims("NATL_ADMIN", "natl_admin", None)

    _override_deps(db, user)
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/v1/admin/state-adapter/TN")
    finally:
        _clear_overrides()

    assert resp.status_code == status.HTTP_200_OK, resp.text
    body = resp.json()
    assert body["success"] is True
    assert len(body["data"]) == 1
    assert body["data"][0]["state_code"] == "TN"


@pytest.mark.anyio
async def test_get_state_adapter_citizen_returns_403():
    """CITIZEN cannot access admin endpoints → 403."""
    db = _make_db_with_configs([])
    user = _make_user_claims("CITIZEN", "citizen1", None)

    _override_deps(db, user)
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/v1/admin/state-adapter/PB")
    finally:
        _clear_overrides()

    assert resp.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.anyio
async def test_get_state_adapter_returns_empty_list():
    """When no configs exist for a state, return an empty list (not 404)."""
    db = _make_db_with_configs([])
    user = _make_user_claims("NATL_ADMIN", "natl_admin", None)

    _override_deps(db, user)
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/v1/admin/state-adapter/XX")
    finally:
        _clear_overrides()

    assert resp.status_code == status.HTTP_200_OK
    body = resp.json()
    assert body["success"] is True
    assert body["data"] == []


# ---------------------------------------------------------------------------
# PUT /admin/state-adapter/{state_code}
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_put_state_adapter_natl_admin_updates_and_writes_audit():
    """PUT by NATL_ADMIN updates config rows and writes UPDATE_STATE_ADAPTER audit."""
    configs = [
        _FakeConfig(id=1, state_code="PB", source_field_name="village_name",
                    canonical_field_name="village_or_city", unit_conversion_factor=1.0),
    ]
    db = _make_db_with_configs(configs)
    user = _make_user_claims("NATL_ADMIN", "natl_admin", None)

    _override_deps(db, user)
    try:
        with patch("routers.admin.write_audit", new_callable=AsyncMock) as mock_audit:
            mock_audit.return_value = MagicMock(id=1, action="UPDATE_STATE_ADAPTER")
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.put(
                    "/api/v1/admin/state-adapter/PB",
                    json={"unit_conversion_factor": 2.5, "language_code": "pa"},
                )
    finally:
        _clear_overrides()

    assert resp.status_code == status.HTTP_200_OK, resp.text
    body = resp.json()
    assert body["success"] is True
    data = body["data"]
    assert len(data) == 1
    # Verify the updated fields are reflected in the response
    assert data[0]["unit_conversion_factor"] == 2.5
    assert data[0]["language_code"] == "pa"

    # Audit entry was written with the correct action
    mock_audit.assert_called_once()
    audit_kwargs = mock_audit.call_args.kwargs
    assert audit_kwargs["action"] == "UPDATE_STATE_ADAPTER"
    assert audit_kwargs["resource_type"] == "state_adapter_config"
    assert audit_kwargs["resource_id"] == "PB"
    assert audit_kwargs["actor_user"] == "natl_admin"
    assert audit_kwargs["actor_role"] == "NATL_ADMIN"

    # DB was committed after audit (audit-before-commit contract)
    db.commit.assert_called_once()


@pytest.mark.anyio
async def test_put_state_adapter_state_admin_returns_403():
    """PUT by STATE_ADMIN → 403 (only NATL_ADMIN may update)."""
    configs = [_FakeConfig(id=1, state_code="PB")]
    db = _make_db_with_configs(configs)
    user = _make_user_claims("STATE_ADMIN", "state_admin", "PB")

    _override_deps(db, user)
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.put(
                "/api/v1/admin/state-adapter/PB",
                json={"unit_conversion_factor": 2.5},
            )
    finally:
        _clear_overrides()

    assert resp.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.anyio
async def test_put_state_adapter_citizen_returns_403():
    """PUT by CITIZEN → 403."""
    configs = [_FakeConfig(id=1, state_code="PB")]
    db = _make_db_with_configs(configs)
    user = _make_user_claims("CITIZEN", "citizen1", None)

    _override_deps(db, user)
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.put(
                "/api/v1/admin/state-adapter/PB",
                json={"unit_conversion_factor": 2.5},
            )
    finally:
        _clear_overrides()

    assert resp.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.anyio
async def test_put_state_adapter_not_found_returns_404():
    """PUT on a state with no adapter config rows → 404."""
    db = _make_db_with_configs([])
    user = _make_user_claims("NATL_ADMIN", "natl_admin", None)

    _override_deps(db, user)
    try:
        with patch("routers.admin.write_audit", new_callable=AsyncMock):
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.put(
                    "/api/v1/admin/state-adapter/ZZ",
                    json={"unit_conversion_factor": 1.0},
                )
    finally:
        _clear_overrides()

    assert resp.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.anyio
async def test_put_state_adapter_partial_update_only_sets_provided_fields():
    """Only fields provided in the request body are updated; others stay unchanged."""
    original_source = "village_name"
    configs = [
        _FakeConfig(id=1, state_code="PB", source_field_name=original_source,
                    canonical_field_name="village_or_city", unit_conversion_factor=1.0,
                    language_code="en"),
    ]
    db = _make_db_with_configs(configs)
    user = _make_user_claims("NATL_ADMIN", "natl_admin", None)

    _override_deps(db, user)
    try:
        with patch("routers.admin.write_audit", new_callable=AsyncMock):
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.put(
                    "/api/v1/admin/state-adapter/PB",
                    json={"language_code": "pa"},  # only language_code
                )
    finally:
        _clear_overrides()

    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()["data"][0]
    # Updated field
    assert data["language_code"] == "pa"
    # Unchanged fields remain at their original values
    assert data["source_field_name"] == original_source
    assert data["unit_conversion_factor"] == 1.0


# ---------------------------------------------------------------------------
# GET /admin/users
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_get_users_natl_admin_returns_all_users_no_password():
    """GET /admin/users by NATL_ADMIN returns all users; hashed_password never exposed."""
    users = [
        _FakeUser(username="admin1", role="STATE_ADMIN", jurisdiction="PB", is_active=True),
        _FakeUser(username="officer1", role="REV_OFF", jurisdiction="TN", is_active=True),
        _FakeUser(username="citizen1", role="CITIZEN", jurisdiction=None, is_active=True),
    ]
    db = _make_db_with_users(users)
    user = _make_user_claims("NATL_ADMIN", "natl_admin", None)

    _override_deps(db, user)
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/v1/admin/users")
    finally:
        _clear_overrides()

    assert resp.status_code == status.HTTP_200_OK, resp.text
    body = resp.json()
    assert body["success"] is True
    data = body["data"]
    assert isinstance(data, list)
    assert len(data) == 3
    for u in data:
        assert "hashed_password" not in u, "hashed_password must never be in output"
        assert "username" in u
        assert "role" in u
        assert "is_active" in u
    usernames = [u["username"] for u in data]
    assert "admin1" in usernames
    assert "officer1" in usernames
    assert "citizen1" in usernames


@pytest.mark.anyio
async def test_get_users_state_admin_scoped_to_own_jurisdiction():
    """GET /admin/users by STATE_ADMIN returns only users in the same jurisdiction."""
    # The mock returns all users, but the router filters by jurisdiction in SQL.
    # We simulate the filtered result by providing only PB users.
    users = [
        _FakeUser(username="admin1", role="STATE_ADMIN", jurisdiction="PB", is_active=True),
        _FakeUser(username="officer_pb", role="REV_OFF", jurisdiction="PB", is_active=True),
    ]
    db = _make_db_with_users(users)
    user = _make_user_claims("STATE_ADMIN", "admin1", "PB")

    _override_deps(db, user)
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/v1/admin/users")
    finally:
        _clear_overrides()

    assert resp.status_code == status.HTTP_200_OK, resp.text
    data = resp.json()["data"]
    # All returned users are in PB (the STATE_ADMIN's jurisdiction)
    for u in data:
        assert "hashed_password" not in u
        assert u["jurisdiction"] == "PB"


@pytest.mark.anyio
async def test_get_users_citizen_returns_403():
    """GET /admin/users by CITIZEN → 403."""
    db = _make_db_with_users([])
    user = _make_user_claims("CITIZEN", "citizen1", None)

    _override_deps(db, user)
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/v1/admin/users")
    finally:
        _clear_overrides()

    assert resp.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.anyio
async def test_get_users_rev_off_returns_403():
    """GET /admin/users by REV_OFF → 403 (only STATE_ADMIN and NATL_ADMIN allowed)."""
    db = _make_db_with_users([])
    user = _make_user_claims("REV_OFF", "rev_off", "PB")

    _override_deps(db, user)
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/v1/admin/users")
    finally:
        _clear_overrides()

    assert resp.status_code == status.HTTP_403_FORBIDDEN
