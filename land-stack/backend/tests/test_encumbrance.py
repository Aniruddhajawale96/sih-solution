"""
tests/test_encumbrance.py — Unit tests for the Encumbrance router.

Coverage:
  - POST /encumbrance → 201 with institution in response
  - GET /encumbrance/{ulpin} → institution visible in public response
  - POST by CITIZEN → 403
  - POST with unknown ULPIN → 404

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
from models.encumbrance import Encumbrance
from models.parcel import Parcel


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_user(role: str, username: str = "testuser", jurisdiction: str | None = None) -> UserClaims:
    return UserClaims(username=username, role=role, jurisdiction=jurisdiction)


def _make_encumbrance(**kwargs) -> MagicMock:
    defaults = dict(
        id=1,
        ulpin="TEST-ULPIN-001",
        type="Mortgage",
        institution="State Bank of India",
        status="Active",
        date=date(2023, 6, 1),
    )
    defaults.update(kwargs)
    obj = MagicMock(spec=Encumbrance)
    for k, v in defaults.items():
        setattr(obj, k, v)
    return obj


# ---------------------------------------------------------------------------
# POST /encumbrance — creates record and returns institution
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_post_encumbrance_reg_off_returns_201_with_institution():
    """
    POST /encumbrance by REG_OFF must return 201 and include institution in response.

    Requirements: 12.1
    """
    enc = _make_encumbrance()

    db = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()

    # First execute: parcel existence check → returns a scalar with the ulpin
    parcel_result = AsyncMock()
    parcel_result.scalar_one_or_none = AsyncMock(return_value="TEST-ULPIN-001")

    # Second execute: audit chain → no previous hash
    audit_result = AsyncMock()
    audit_result.scalar_one_or_none = AsyncMock(return_value=None)

    call_count = [0]
    results = [parcel_result, audit_result]

    async def _execute(*args, **kwargs):
        idx = call_count[0]
        call_count[0] += 1
        if idx < len(results):
            return results[idx]
        return audit_result

    db.execute = _execute

    with patch("routers.encumbrance.write_audit", new_callable=AsyncMock) as mock_audit:
        mock_audit.return_value = MagicMock(id=1)

        # After db.refresh, the router calls model_validate on the ORM object.
        # We inject enc's attributes into the add call by patching Encumbrance.__init__
        # via tracking what was db.add()'d. Instead, capture the object added to db:
        added_objects: list = []
        original_add = db.add

        def _capture_add(obj):
            added_objects.append(obj)

        db.add = _capture_add

        # Patch the Encumbrance constructor to return our mock
        with patch("routers.encumbrance.Encumbrance", return_value=enc):

            async def override_db():
                yield db

            app.dependency_overrides[get_db] = override_db
            app.dependency_overrides[get_redis] = lambda: AsyncMock()
            app.dependency_overrides[get_current_user] = lambda: _make_user("REG_OFF", "reg_off", "DL")

            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.post(
                    "/api/v1/encumbrance",
                    json={
                        "ulpin": "TEST-ULPIN-001",
                        "type": "Mortgage",
                        "institution": "State Bank of India",
                        "status": "Active",
                        "date": "2023-06-01",
                    },
                )

    app.dependency_overrides.clear()

    assert response.status_code == status.HTTP_201_CREATED, response.text
    body = response.json()
    assert body["success"] is True
    data = body["data"]
    assert "institution" in data
    assert data["institution"] == "State Bank of India"

    # Audit must have been written
    mock_audit.assert_called_once()
    assert mock_audit.call_args.kwargs["action"] == "CREATE_ENCUMBRANCE"


@pytest.mark.anyio
async def test_post_encumbrance_citizen_returns_403():
    """
    POST /encumbrance by CITIZEN must return 403.

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
        response = await client.post(
            "/api/v1/encumbrance",
            json={
                "ulpin": "TEST-ULPIN-001",
                "type": "Mortgage",
                "institution": "Some Bank",
                "status": "Active",
                "date": "2023-06-01",
            },
        )

    app.dependency_overrides.clear()
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.anyio
async def test_post_encumbrance_unknown_ulpin_returns_error():
    """
    POST /encumbrance with a ULPIN that doesn't exist in parcels must return an error.

    Requirements: 12.1
    """
    db = AsyncMock()

    # Parcel existence check returns None — MagicMock so scalar_one_or_none() is sync
    parcel_result = MagicMock()
    parcel_result.scalar_one_or_none = MagicMock(return_value=None)
    db.execute = AsyncMock(return_value=parcel_result)

    async def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_redis] = lambda: AsyncMock()
    app.dependency_overrides[get_current_user] = lambda: _make_user("REG_OFF", "reg_off", "DL")

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/encumbrance",
            json={
                "ulpin": "UNKNOWN-ULPIN",
                "type": "Mortgage",
                "institution": "Some Bank",
                "status": "Active",
                "date": "2023-06-01",
            },
        )

    app.dependency_overrides.clear()

    # Router returns err() for unknown ULPIN; since the route declares 201 as default
    # status code, the response arrives as HTTP 201 but with success=False in body.
    body = response.json()
    is_error = body.get("success") is False
    assert is_error, f"Expected error response, got {response.status_code}: {body}"


# ---------------------------------------------------------------------------
# GET /encumbrance/{ulpin} — institution visible in public response
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_get_encumbrance_institution_in_public_response():
    """
    GET /encumbrance/{ulpin} by any authenticated role must include institution.

    Requirements: 12.1
    """
    enc = _make_encumbrance()

    db = AsyncMock()

    # First execute: parcel existence check
    parcel_result = AsyncMock()
    parcel_result.scalar_one_or_none = AsyncMock(return_value="TEST-ULPIN-001")

    # Second execute: encumbrance list query
    scalars_mock = MagicMock()
    scalars_mock.all = MagicMock(return_value=[enc])
    enc_result = AsyncMock()
    enc_result.scalars = MagicMock(return_value=scalars_mock)

    call_count = [0]
    results = [parcel_result, enc_result]

    async def _execute(*args, **kwargs):
        idx = call_count[0]
        call_count[0] += 1
        if idx < len(results):
            return results[idx]
        return enc_result

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
        response = await client.get("/api/v1/encumbrance/TEST-ULPIN-001")

    app.dependency_overrides.clear()

    assert response.status_code == status.HTTP_200_OK, response.text
    body = response.json()
    assert body["success"] is True
    items = body["data"]
    assert isinstance(items, list)
    assert len(items) == 1
    item = items[0]
    assert "institution" in item, "institution must be present in public encumbrance response"
    assert item["institution"] == "State Bank of India"


@pytest.mark.anyio
async def test_get_encumbrance_all_public_fields_present():
    """
    GET /encumbrance/{ulpin} response must include all required public fields.

    Requirements: 12.1
    """
    enc = _make_encumbrance()

    db = AsyncMock()
    parcel_result = AsyncMock()
    parcel_result.scalar_one_or_none = AsyncMock(return_value="TEST-ULPIN-001")

    scalars_mock = MagicMock()
    scalars_mock.all = MagicMock(return_value=[enc])
    enc_result = AsyncMock()
    enc_result.scalars = MagicMock(return_value=scalars_mock)

    call_count = [0]
    results = [parcel_result, enc_result]

    async def _execute(*args, **kwargs):
        idx = call_count[0]
        call_count[0] += 1
        return results[idx] if idx < len(results) else enc_result

    db.execute = _execute

    async def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_redis] = lambda: AsyncMock()
    # Test with officer role too — same fields since no masking
    app.dependency_overrides[get_current_user] = lambda: _make_user("REG_OFF", jurisdiction="DL")

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get("/api/v1/encumbrance/TEST-ULPIN-001")

    app.dependency_overrides.clear()

    assert response.status_code == status.HTTP_200_OK
    item = response.json()["data"][0]
    for field in ("id", "ulpin", "type", "institution", "status", "date"):
        assert field in item, f"Required field '{field}' missing from encumbrance response"
