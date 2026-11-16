"""
tests/test_building_permission.py — Unit tests for the Building Permission router.

Coverage:
  - POST /building-permission by PLAN_OFF → 201 + audit row written
  - GET /building-permission/{ulpin} → 200 public response with all required fields
  - POST by CITIZEN → 403
  - POST with unknown ULPIN → 404
  - GET for unknown ULPIN → 404

Tests use httpx.AsyncClient with FastAPI's ASGI transport.
Dependency overrides replace get_db and get_current_user.
No live PostgreSQL or Redis connection required.

Requirements: 12.1, 12.2
"""

from __future__ import annotations

import sys
import os
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import httpx
from fastapi import status

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from main import app
from core.rbac import UserClaims, get_current_user
from core.database import get_db
from core.redis_client import get_redis
from models.building_permission import BuildingPermission


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_user(role: str, username: str = "testuser", jurisdiction: str | None = None) -> UserClaims:
    return UserClaims(username=username, role=role, jurisdiction=jurisdiction)


def _make_bp(**kwargs) -> MagicMock:
    """Return a mock BuildingPermission ORM object with sensible defaults."""
    defaults = dict(
        id=1,
        ulpin="TEST-ULPIN-001",
        approval_no="BP-2024-001",
        approved_built_up_area=120.5,
        approval_date=date(2024, 2, 20),
        status="Approved",
        architect_ref="ARCH-REF-001",
    )
    defaults.update(kwargs)
    obj = MagicMock(spec=BuildingPermission)
    for k, v in defaults.items():
        setattr(obj, k, v)
    return obj


_POST_PAYLOAD = {
    "ulpin": "TEST-ULPIN-001",
    "approval_no": "BP-2024-001",
    "approved_built_up_area": 120.5,
    "approval_date": "2024-02-20",
    "status": "Approved",
    "architect_ref": "ARCH-REF-001",
}


# ---------------------------------------------------------------------------
# POST /building-permission — PLAN_OFF → 201 + audit
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_post_building_permission_plan_off_returns_201():
    """
    POST /building-permission by PLAN_OFF must return 201 and write an audit entry.

    Requirements: 12.1
    """
    bp = _make_bp()

    db = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()

    # First execute: parcel existence check → returns parcel ulpin
    parcel_result = AsyncMock()
    parcel_result.scalar_one_or_none = AsyncMock(return_value="TEST-ULPIN-001")

    # Subsequent execute calls (for audit chain)
    audit_result = AsyncMock()
    audit_result.scalar_one_or_none = AsyncMock(return_value=None)

    call_count = [0]
    results = [parcel_result, audit_result]

    async def _execute(*args, **kwargs):
        idx = call_count[0]
        call_count[0] += 1
        return results[idx] if idx < len(results) else audit_result

    db.execute = _execute

    # After db.refresh the router calls model_validate on the ORM object.
    async def _refresh(obj):
        pass  # bp attributes are already set via patch below

    db.refresh = AsyncMock(side_effect=_refresh)

    with patch("routers.building_permission.write_audit", new_callable=AsyncMock) as mock_audit, \
         patch("routers.building_permission.BuildingPermission", return_value=bp):

        async def override_db():
            yield db

        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[get_redis] = lambda: AsyncMock()
        app.dependency_overrides[get_current_user] = lambda: _make_user("PLAN_OFF", "plan_off", "DL")

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post("/api/v1/building-permission", json=_POST_PAYLOAD)

    app.dependency_overrides.clear()

    assert response.status_code == status.HTTP_201_CREATED, response.text
    body = response.json()
    assert body["success"] is True

    # Audit entry must have been written
    mock_audit.assert_called_once()
    kw = mock_audit.call_args.kwargs
    assert kw["action"] == "CREATE_BUILDING_PERMISSION"
    assert kw["actor_role"] == "PLAN_OFF"
    assert kw["resource_type"] == "building_permission"


@pytest.mark.anyio
async def test_post_building_permission_response_fields():
    """
    POST /building-permission response must include all required fields.

    Requirements: 12.1
    """
    bp = _make_bp()

    db = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()

    parcel_result = AsyncMock()
    parcel_result.scalar_one_or_none = AsyncMock(return_value="TEST-ULPIN-001")
    db.execute = AsyncMock(return_value=parcel_result)

    with patch("routers.building_permission.write_audit", new_callable=AsyncMock), \
         patch("routers.building_permission.BuildingPermission", return_value=bp):

        async def override_db():
            yield db

        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[get_redis] = lambda: AsyncMock()
        app.dependency_overrides[get_current_user] = lambda: _make_user("STATE_ADMIN", "sadmin", "DL")

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post("/api/v1/building-permission", json=_POST_PAYLOAD)

    app.dependency_overrides.clear()

    assert response.status_code == status.HTTP_201_CREATED, response.text
    data = response.json()["data"]
    for field in ("id", "ulpin", "approval_no", "approved_built_up_area", "approval_date", "status"):
        assert field in data, f"Required field '{field}' missing from building permission response"


# ---------------------------------------------------------------------------
# POST /building-permission — CITIZEN → 403
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_post_building_permission_citizen_returns_403():
    """
    POST /building-permission by CITIZEN must return 403.

    Requirements: 12.2
    """
    db = AsyncMock()

    async def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_redis] = lambda: AsyncMock()
    app.dependency_overrides[get_current_user] = lambda: _make_user("CITIZEN")

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post("/api/v1/building-permission", json=_POST_PAYLOAD)

    app.dependency_overrides.clear()
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.anyio
async def test_post_building_permission_rev_off_returns_403():
    """
    POST /building-permission by REV_OFF (not in write roles) must return 403.

    Requirements: 12.2
    """
    db = AsyncMock()

    async def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_redis] = lambda: AsyncMock()
    app.dependency_overrides[get_current_user] = lambda: _make_user("REV_OFF", jurisdiction="DL")

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post("/api/v1/building-permission", json=_POST_PAYLOAD)

    app.dependency_overrides.clear()
    assert response.status_code == status.HTTP_403_FORBIDDEN


# ---------------------------------------------------------------------------
# POST /building-permission — unknown ULPIN → 404
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_post_building_permission_unknown_ulpin_returns_404():
    """
    POST /building-permission with a ULPIN that doesn't exist in parcels must return 404.

    Requirements: 12.1
    """
    db = AsyncMock()
    parcel_result = MagicMock()
    parcel_result.scalar_one_or_none = MagicMock(return_value=None)
    db.execute = AsyncMock(return_value=parcel_result)

    async def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_redis] = lambda: AsyncMock()
    app.dependency_overrides[get_current_user] = lambda: _make_user("PLAN_OFF", "plan_off", "DL")

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/building-permission",
            json={**_POST_PAYLOAD, "ulpin": "UNKNOWN-ULPIN"},
        )

    app.dependency_overrides.clear()
    assert response.status_code == status.HTTP_404_NOT_FOUND, response.text


# ---------------------------------------------------------------------------
# GET /building-permission/{ulpin} — public response with all required fields
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_get_building_permission_citizen_returns_200_with_all_fields():
    """
    GET /building-permission/{ulpin} by any authenticated role must return 200
    with all required public fields (id, ulpin, approval_no, etc.).

    Requirements: 12.1
    """
    bp = _make_bp()

    db = AsyncMock()

    # First execute: parcel existence check
    parcel_result = AsyncMock()
    parcel_result.scalar_one_or_none = AsyncMock(return_value="TEST-ULPIN-001")

    # Second execute: building permission list query
    scalars_mock = MagicMock()
    scalars_mock.all = MagicMock(return_value=[bp])
    bp_result = AsyncMock()
    bp_result.scalars = MagicMock(return_value=scalars_mock)

    call_count = [0]
    results = [parcel_result, bp_result]

    async def _execute(*args, **kwargs):
        idx = call_count[0]
        call_count[0] += 1
        return results[idx] if idx < len(results) else bp_result

    db.execute = _execute

    async def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_redis] = lambda: AsyncMock()
    app.dependency_overrides[get_current_user] = lambda: _make_user("CITIZEN")

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get("/api/v1/building-permission/TEST-ULPIN-001")

    app.dependency_overrides.clear()

    assert response.status_code == status.HTTP_200_OK, response.text
    body = response.json()
    assert body["success"] is True
    items = body["data"]
    assert isinstance(items, list)
    assert len(items) == 1
    item = items[0]
    for field in ("id", "ulpin", "approval_no", "approved_built_up_area", "approval_date", "status"):
        assert field in item, f"Required field '{field}' missing from building permission public response"
    assert item["ulpin"] == "TEST-ULPIN-001"
    assert item["approval_no"] == "BP-2024-001"


@pytest.mark.anyio
async def test_get_building_permission_officer_returns_200():
    """
    GET /building-permission/{ulpin} by PLAN_OFF must also return 200 with same fields
    (no masking — building permission data is fully public).

    Requirements: 12.1
    """
    bp = _make_bp()

    db = AsyncMock()
    parcel_result = AsyncMock()
    parcel_result.scalar_one_or_none = AsyncMock(return_value="TEST-ULPIN-001")

    scalars_mock = MagicMock()
    scalars_mock.all = MagicMock(return_value=[bp])
    bp_result = AsyncMock()
    bp_result.scalars = MagicMock(return_value=scalars_mock)

    call_count = [0]
    results = [parcel_result, bp_result]

    async def _execute(*args, **kwargs):
        idx = call_count[0]
        call_count[0] += 1
        return results[idx] if idx < len(results) else bp_result

    db.execute = _execute

    async def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_redis] = lambda: AsyncMock()
    app.dependency_overrides[get_current_user] = lambda: _make_user("PLAN_OFF", jurisdiction="DL")

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get("/api/v1/building-permission/TEST-ULPIN-001")

    app.dependency_overrides.clear()

    assert response.status_code == status.HTTP_200_OK, response.text
    items = response.json()["data"]
    assert len(items) == 1
    assert items[0]["approval_no"] == "BP-2024-001"


# ---------------------------------------------------------------------------
# GET /building-permission/{ulpin} — unknown ULPIN → 404
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_get_building_permission_unknown_ulpin_returns_404():
    """
    GET /building-permission/{ulpin} for a non-existent ULPIN must return 404.

    Requirements: 12.2
    """
    db = AsyncMock()
    parcel_result = MagicMock()
    parcel_result.scalar_one_or_none = MagicMock(return_value=None)
    db.execute = AsyncMock(return_value=parcel_result)

    async def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_redis] = lambda: AsyncMock()
    app.dependency_overrides[get_current_user] = lambda: _make_user("CITIZEN")

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get("/api/v1/building-permission/UNKNOWN-ULPIN")

    app.dependency_overrides.clear()
    assert response.status_code == status.HTTP_404_NOT_FOUND, response.text


# ---------------------------------------------------------------------------
# GET /building-permission/{ulpin} — empty list when no records exist
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_get_building_permission_empty_list_when_no_records():
    """
    GET /building-permission/{ulpin} returns an empty list when the parcel has no permits.

    Requirements: 12.1
    """
    db = AsyncMock()
    parcel_result = AsyncMock()
    parcel_result.scalar_one_or_none = AsyncMock(return_value="TEST-ULPIN-002")

    scalars_mock = MagicMock()
    scalars_mock.all = MagicMock(return_value=[])
    bp_result = AsyncMock()
    bp_result.scalars = MagicMock(return_value=scalars_mock)

    call_count = [0]
    results = [parcel_result, bp_result]

    async def _execute(*args, **kwargs):
        idx = call_count[0]
        call_count[0] += 1
        return results[idx] if idx < len(results) else bp_result

    db.execute = _execute

    async def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_redis] = lambda: AsyncMock()
    app.dependency_overrides[get_current_user] = lambda: _make_user("CITIZEN")

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get("/api/v1/building-permission/TEST-ULPIN-002")

    app.dependency_overrides.clear()

    assert response.status_code == status.HTTP_200_OK, response.text
    body = response.json()
    assert body["success"] is True
    assert body["data"] == []
