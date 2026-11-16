"""
tests/test_tax.py — Unit tests for the Tax router.

Coverage:
  - GET /tax/{ulpin} by CITIZEN → TaxPublic (annual_tax absent)
  - GET /tax/{ulpin} by TAX_OFF → TaxInternal (annual_tax present)
  - PUT /tax/{ulpin} by TAX_OFF → updates tax record and writes REASSESS_TAX audit
  - PUT /tax/{ulpin} by CITIZEN → 403
  - GET / PUT for unknown ULPIN → 404

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
from models.tax import Tax


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_user(role: str, username: str = "testuser", jurisdiction: str | None = None) -> UserClaims:
    return UserClaims(username=username, role=role, jurisdiction=jurisdiction)


def _make_tax(**kwargs) -> MagicMock:
    defaults = dict(
        ulpin="TEST-ULPIN-001",
        assessment_id="ASSESS-2024-001",
        annual_tax=12000,
        last_paid_date=date(2024, 3, 31),
        payment_status="Paid",
        arrears=0,
    )
    defaults.update(kwargs)
    obj = MagicMock(spec=Tax)
    for k, v in defaults.items():
        setattr(obj, k, v)
    return obj


def _make_execute_returning(obj):
    """Return an async execute that always yields a sync scalar_one_or_none() = obj."""
    result = MagicMock()
    result.scalar_one_or_none = MagicMock(return_value=obj)

    async def _execute(*args, **kwargs):
        return result

    return _execute


def _make_execute_sequence(*objs):
    """Return an async execute that yields successive MagicMock results each call."""
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
# GET /tax/{ulpin} — CITIZEN omits annual_tax
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_get_tax_citizen_omits_annual_tax():
    """
    GET /tax/{ulpin} by CITIZEN must return TaxPublic with annual_tax absent.

    Requirements: 12.1, 12.2
    """
    tax = _make_tax()

    db = AsyncMock()
    db.execute = _make_execute_returning(tax)

    async def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_redis] = lambda: AsyncMock()
    app.dependency_overrides[get_current_user] = lambda: _make_user("CITIZEN")

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get("/api/v1/tax/TEST-ULPIN-001")

    app.dependency_overrides.clear()

    assert response.status_code == status.HTTP_200_OK, response.text
    body = response.json()
    assert body["success"] is True
    data = body["data"]
    assert "annual_tax" not in data, (
        "CITIZEN must not see annual_tax in tax response"
    )


@pytest.mark.anyio
async def test_get_tax_citizen_receives_public_fields():
    """
    GET /tax/{ulpin} by CITIZEN must include arrears and payment_status.

    Requirements: 12.1
    """
    tax = _make_tax(arrears=5000, payment_status="Overdue")

    db = AsyncMock()
    db.execute = _make_execute_returning(tax)

    async def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_redis] = lambda: AsyncMock()
    app.dependency_overrides[get_current_user] = lambda: _make_user("CITIZEN")

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get("/api/v1/tax/TEST-ULPIN-001")

    app.dependency_overrides.clear()

    assert response.status_code == status.HTTP_200_OK
    data = response.json()["data"]
    assert "arrears" in data
    assert data["arrears"] == 5000
    assert "payment_status" in data
    assert data["payment_status"] == "Overdue"
    assert "annual_tax" not in data


# ---------------------------------------------------------------------------
# GET /tax/{ulpin} — TAX_OFF receives annual_tax
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_get_tax_tax_off_includes_annual_tax():
    """
    GET /tax/{ulpin} by TAX_OFF must return TaxInternal with annual_tax present.

    Requirements: 12.1
    """
    tax = _make_tax(annual_tax=12000)

    db = AsyncMock()
    db.execute = _make_execute_returning(tax)

    async def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_redis] = lambda: AsyncMock()
    app.dependency_overrides[get_current_user] = lambda: _make_user("TAX_OFF", "tax_off", "DL")

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get("/api/v1/tax/TEST-ULPIN-001")

    app.dependency_overrides.clear()

    assert response.status_code == status.HTTP_200_OK, response.text
    data = response.json()["data"]
    assert "annual_tax" in data, "TAX_OFF must receive annual_tax in tax response"
    assert data["annual_tax"] == 12000


@pytest.mark.anyio
async def test_get_tax_state_admin_includes_annual_tax():
    """
    GET /tax/{ulpin} by STATE_ADMIN must include annual_tax (internal view).

    Requirements: 12.1
    """
    tax = _make_tax(annual_tax=8500)

    db = AsyncMock()
    db.execute = _make_execute_returning(tax)

    async def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_redis] = lambda: AsyncMock()
    app.dependency_overrides[get_current_user] = lambda: _make_user("STATE_ADMIN", "sadmin", "DL")

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get("/api/v1/tax/TEST-ULPIN-001")

    app.dependency_overrides.clear()

    assert response.status_code == status.HTTP_200_OK
    data = response.json()["data"]
    assert "annual_tax" in data
    assert data["annual_tax"] == 8500


# ---------------------------------------------------------------------------
# GET /tax/{ulpin} — 404 for unknown ULPIN
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_get_tax_unknown_ulpin_returns_404():
    """
    GET /tax/{ulpin} for a non-existent ULPIN must return 404.

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
        response = await client.get("/api/v1/tax/UNKNOWN-ULPIN")

    app.dependency_overrides.clear()
    assert response.status_code == status.HTTP_404_NOT_FOUND


# ---------------------------------------------------------------------------
# PUT /tax/{ulpin} — TAX_OFF writes audit
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_put_tax_tax_off_writes_reassess_tax_audit():
    """
    PUT /tax/{ulpin} by TAX_OFF must call write_audit with action=REASSESS_TAX.

    Requirements: 12.1
    """

    class _TaxMock:
        ulpin = "TEST-ULPIN-001"
        assessment_id = "ASSESS-2024-001"
        annual_tax = 12000
        last_paid_date = date(2024, 3, 31)
        payment_status = "Paid"
        arrears = 0

    tax_obj = _TaxMock()

    db = AsyncMock()
    db.execute = _make_execute_sequence(tax_obj)
    db.commit = AsyncMock()
    db.refresh = AsyncMock()

    with patch("routers.tax.write_audit", new_callable=AsyncMock) as mock_audit:
        mock_audit.return_value = MagicMock(id=1)

        async def override_db():
            yield db

        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[get_redis] = lambda: AsyncMock()
        app.dependency_overrides[get_current_user] = lambda: _make_user("TAX_OFF", "tax_off", "DL")

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.put(
                "/api/v1/tax/TEST-ULPIN-001",
                json={"annual_tax": 15000},
            )

    app.dependency_overrides.clear()

    assert response.status_code == status.HTTP_200_OK, response.text
    body = response.json()
    assert body["success"] is True

    # Audit entry must have been written
    mock_audit.assert_called_once()
    kw = mock_audit.call_args.kwargs
    assert kw["action"] == "REASSESS_TAX"
    assert kw["actor_role"] == "TAX_OFF"
    assert kw["resource_type"] == "tax"
    assert kw["resource_id"] == "TEST-ULPIN-001"


@pytest.mark.anyio
async def test_put_tax_response_includes_annual_tax():
    """
    PUT /tax/{ulpin} by TAX_OFF must return TaxInternal with annual_tax present.

    Requirements: 12.1
    """

    class _TaxMock:
        ulpin = "TEST-ULPIN-001"
        assessment_id = "ASSESS-2024-001"
        annual_tax = 12000
        last_paid_date = date(2024, 3, 31)
        payment_status = "Paid"
        arrears = 0

    tax_obj = _TaxMock()

    db = AsyncMock()
    db.execute = _make_execute_sequence(tax_obj)
    db.commit = AsyncMock()
    db.refresh = AsyncMock()

    with patch("routers.tax.write_audit", new_callable=AsyncMock) as mock_audit:
        mock_audit.return_value = MagicMock(id=1)

        async def override_db():
            yield db

        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[get_redis] = lambda: AsyncMock()
        app.dependency_overrides[get_current_user] = lambda: _make_user("TAX_OFF", "tax_off", "DL")

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.put(
                "/api/v1/tax/TEST-ULPIN-001",
                json={"payment_status": "Overdue", "arrears": 3000},
            )

    app.dependency_overrides.clear()

    assert response.status_code == status.HTTP_200_OK
    data = response.json()["data"]
    assert "annual_tax" in data, "PUT response must include annual_tax (TaxInternal)"


# ---------------------------------------------------------------------------
# PUT /tax/{ulpin} — CITIZEN → 403
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_put_tax_citizen_returns_403():
    """
    PUT /tax/{ulpin} by CITIZEN must return 403.

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
            "/api/v1/tax/TEST-ULPIN-001",
            json={"annual_tax": 10000},
        )

    app.dependency_overrides.clear()
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.anyio
async def test_put_tax_rev_off_returns_403():
    """
    PUT /tax/{ulpin} by REV_OFF (not in write roles) must return 403.

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
        response = await client.put(
            "/api/v1/tax/TEST-ULPIN-001",
            json={"annual_tax": 10000},
        )

    app.dependency_overrides.clear()
    assert response.status_code == status.HTTP_403_FORBIDDEN


# ---------------------------------------------------------------------------
# PUT /tax/{ulpin} — 404 for unknown ULPIN
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_put_tax_unknown_ulpin_returns_404():
    """
    PUT /tax/{ulpin} for a non-existent ULPIN must return 404.

    Requirements: 12.2
    """
    db = AsyncMock()
    db.execute = _make_execute_returning(None)

    async def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_redis] = lambda: AsyncMock()
    app.dependency_overrides[get_current_user] = lambda: _make_user("TAX_OFF", jurisdiction="DL")

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.put(
            "/api/v1/tax/UNKNOWN-ULPIN",
            json={"annual_tax": 10000},
        )

    app.dependency_overrides.clear()
    assert response.status_code == status.HTTP_404_NOT_FOUND
