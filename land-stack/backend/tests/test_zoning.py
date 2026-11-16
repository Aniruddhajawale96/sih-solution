"""
tests/test_zoning.py — Unit tests for the Zoning router.

Coverage:
  - PUT /zoning/{ulpin} → updates record, violation_flag computed correctly
  - GET /zoning/{ulpin} → returns zoning record with violation_flag
  - violation_flag is True when far_existing > far_permitted, False otherwise
  - PUT by CITIZEN → 403
  - GET / PUT for unknown ULPIN → 404

Requirements: 12.1, 12.2
"""

from __future__ import annotations

import sys
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import httpx
from fastapi import status

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from main import app
from core.rbac import UserClaims, get_current_user
from core.database import get_db
from core.redis_client import get_redis
from models.zoning import Zoning


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_user(role: str, username: str = "testuser", jurisdiction: str | None = None) -> UserClaims:
    return UserClaims(username=username, role=role, jurisdiction=jurisdiction)


def _make_zoning(**kwargs) -> MagicMock:
    defaults = dict(
        ulpin="TEST-ULPIN-001",
        master_plan_zone="Residential",
        permissible_use="Dwelling",
        far_permitted=2.0,
        far_existing=1.5,
        violation_flag=False,
    )
    defaults.update(kwargs)
    obj = MagicMock(spec=Zoning)
    for k, v in defaults.items():
        setattr(obj, k, v)
    return obj


def _make_execute_returning(obj):
    """Return an async execute function whose result.scalar_one_or_none() returns obj."""
    result = MagicMock()
    result.scalar_one_or_none = MagicMock(return_value=obj)

    async def _execute(*args, **kwargs):
        return result

    return _execute


def _make_execute_sequence(*objs):
    """Return an async execute function that cycles through objs on each call."""
    call_count = [0]

    async def _execute(*args, **kwargs):
        idx = call_count[0]
        call_count[0] += 1
        obj = objs[idx] if idx < len(objs) else objs[-1]
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=obj)
        return result

    return _execute


# ---------------------------------------------------------------------------
# PUT /zoning/{ulpin} — violation_flag computed from far values
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_put_zoning_sets_violation_flag_false_when_far_ok():
    """
    PUT /zoning/{ulpin}: when far_existing (1.5) < far_permitted (2.0),
    violation_flag must be False after the update.

    Requirements: 12.1
    """

    class _ZoningMock:
        ulpin = "TEST-ULPIN-001"
        master_plan_zone = "Residential"
        permissible_use = "Dwelling"
        far_permitted = 2.0
        far_existing = 1.5
        violation_flag = False

    zoning_obj = _ZoningMock()

    db = AsyncMock()
    db.execute = _make_execute_sequence(zoning_obj)
    db.commit = AsyncMock()
    db.refresh = AsyncMock()

    with patch("routers.zoning.write_audit", new_callable=AsyncMock) as mock_audit:
        mock_audit.return_value = MagicMock(id=1)

        async def override_db():
            yield db

        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[get_redis] = lambda: AsyncMock()
        app.dependency_overrides[get_current_user] = lambda: _make_user("PLAN_OFF", "plan_off", "DL")

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.put(
                "/api/v1/zoning/TEST-ULPIN-001",
                json={"far_permitted": 2.0},
            )

    app.dependency_overrides.clear()

    assert response.status_code == status.HTTP_200_OK, response.text
    body = response.json()
    assert body["success"] is True
    # far_existing (1.5) < far_permitted (2.0) → no violation
    assert body["data"]["violation_flag"] is False


@pytest.mark.anyio
async def test_put_zoning_violation_flag_true_when_far_existing_greater():
    """
    PUT /zoning/{ulpin} must set violation_flag=True when far_existing > far_permitted.
    Uses a zoning object where far_existing is already > far_permitted.

    Requirements: 12.1
    """

    class _ZoningMock:
        ulpin = "TEST-ULPIN-001"
        master_plan_zone = "Residential"
        permissible_use = "Dwelling"
        far_permitted = 1.0
        far_existing = 2.5
        violation_flag = False

    zoning_obj = _ZoningMock()

    db = AsyncMock()
    db.execute = _make_execute_sequence(zoning_obj)
    db.commit = AsyncMock()
    db.refresh = AsyncMock()

    with patch("routers.zoning.write_audit", new_callable=AsyncMock) as mock_audit:
        mock_audit.return_value = MagicMock(id=1)

        async def override_db():
            yield db

        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[get_redis] = lambda: AsyncMock()
        app.dependency_overrides[get_current_user] = lambda: _make_user("PLAN_OFF", "plan_off", "DL")

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.put(
                "/api/v1/zoning/TEST-ULPIN-001",
                json={"permissible_use": "Commercial"},
            )

    app.dependency_overrides.clear()

    assert response.status_code == status.HTTP_200_OK, response.text
    data = response.json()["data"]
    # far_existing (2.5) > far_permitted (1.0) → violation
    assert data["violation_flag"] is True, (
        "violation_flag must be True when far_existing > far_permitted"
    )


@pytest.mark.anyio
async def test_put_zoning_citizen_returns_403():
    """
    PUT /zoning/{ulpin} by CITIZEN must return 403.

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
        response = await client.put(
            "/api/v1/zoning/TEST-ULPIN-001",
            json={"permissible_use": "Commercial"},
        )

    app.dependency_overrides.clear()
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.anyio
async def test_put_zoning_unknown_ulpin_returns_404():
    """
    PUT /zoning/{ulpin} for a non-existent ULPIN must return 404.

    Requirements: 12.2
    """
    db = AsyncMock()
    db.execute = _make_execute_returning(None)

    async def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_redis] = lambda: AsyncMock()
    app.dependency_overrides[get_current_user] = lambda: _make_user("PLAN_OFF", jurisdiction="DL")

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.put(
            "/api/v1/zoning/UNKNOWN-ULPIN",
            json={"permissible_use": "Commercial"},
        )

    app.dependency_overrides.clear()
    assert response.status_code == status.HTTP_404_NOT_FOUND


# ---------------------------------------------------------------------------
# GET /zoning/{ulpin}
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_get_zoning_returns_violation_flag():
    """
    GET /zoning/{ulpin} must return violation_flag reflecting the stored value.

    Requirements: 12.1
    """
    zoning = _make_zoning(far_permitted=1.5, far_existing=2.0, violation_flag=True)

    db = AsyncMock()
    db.execute = _make_execute_returning(zoning)

    async def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_redis] = lambda: AsyncMock()
    app.dependency_overrides[get_current_user] = lambda: _make_user("CITIZEN")

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get("/api/v1/zoning/TEST-ULPIN-001")

    app.dependency_overrides.clear()

    assert response.status_code == status.HTTP_200_OK, response.text
    data = response.json()["data"]
    assert "violation_flag" in data
    assert data["violation_flag"] is True


@pytest.mark.anyio
async def test_get_zoning_violation_flag_false_when_compliant():
    """
    GET /zoning/{ulpin} returns violation_flag=False when far_existing <= far_permitted.

    Requirements: 12.1
    """
    zoning = _make_zoning(far_permitted=2.0, far_existing=1.0, violation_flag=False)

    db = AsyncMock()
    db.execute = _make_execute_returning(zoning)

    async def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_redis] = lambda: AsyncMock()
    app.dependency_overrides[get_current_user] = lambda: _make_user("CITIZEN")

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get("/api/v1/zoning/TEST-ULPIN-001")

    app.dependency_overrides.clear()

    assert response.status_code == status.HTTP_200_OK
    data = response.json()["data"]
    assert data["violation_flag"] is False


@pytest.mark.anyio
async def test_get_zoning_unknown_ulpin_returns_404():
    """
    GET /zoning/{ulpin} for a non-existent ULPIN must return 404.

    Requirements: 12.2
    """
    db = AsyncMock()
    db.execute = _make_execute_returning(None)

    async def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_redis] = lambda: AsyncMock()
    app.dependency_overrides[get_current_user] = lambda: _make_user("CITIZEN")

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get("/api/v1/zoning/UNKNOWN-ULPIN")

    app.dependency_overrides.clear()
    assert response.status_code == status.HTTP_404_NOT_FOUND


# ---------------------------------------------------------------------------
# PUT /zoning/{ulpin} — audit entry written
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_put_zoning_audit_written():
    """
    PUT /zoning/{ulpin} must call write_audit with action=UPDATE_ZONING.

    Requirements: 12.1
    """

    class _ZoningMock:
        ulpin = "TEST-ULPIN-001"
        master_plan_zone = "Residential"
        permissible_use = "Dwelling"
        far_permitted = 2.0
        far_existing = 1.0
        violation_flag = False

    zoning_obj = _ZoningMock()

    db = AsyncMock()
    db.execute = _make_execute_sequence(zoning_obj)
    db.commit = AsyncMock()
    db.refresh = AsyncMock()

    with patch("routers.zoning.write_audit", new_callable=AsyncMock) as mock_audit:
        mock_audit.return_value = MagicMock(id=1)

        async def override_db():
            yield db

        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[get_redis] = lambda: AsyncMock()
        app.dependency_overrides[get_current_user] = lambda: _make_user("STATE_ADMIN", "sadmin", "DL")

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.put(
                "/api/v1/zoning/TEST-ULPIN-001",
                json={"far_permitted": 3.0},
            )

    app.dependency_overrides.clear()

    assert response.status_code == status.HTTP_200_OK, response.text
    mock_audit.assert_called_once()
    kw = mock_audit.call_args.kwargs
    assert kw["action"] == "UPDATE_ZONING"
    assert kw["resource_type"] == "zoning"
    assert kw["resource_id"] == "TEST-ULPIN-001"
