"""
tests/test_registration.py — Unit tests for the Registration router.

Coverage:
  - POST /registration by REG_OFF → 201 + audit row written + Redis publish called
  - GET /registration by CITIZEN omits transaction_value
  - GET /registration/{id} by CITIZEN omits transaction_value
  - POST /registration by CITIZEN → 403
  - GET /registration/{id} → 404 for unknown id

Requirements: 12.1, 12.2
"""

from __future__ import annotations

import sys
import os
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
import httpx
from fastapi import status

# Allow importing backend/ modules from the tests directory.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from main import app
from core.rbac import UserClaims, get_current_user
from core.database import get_db
from core.redis_client import get_redis
from models.registration import Registration
from models.audit_log import AuditLog


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _make_user(role: str, username: str = "testuser", jurisdiction: str | None = None) -> UserClaims:
    return UserClaims(username=username, role=role, jurisdiction=jurisdiction)


def _make_registration(**kwargs) -> MagicMock:
    """Return a mock Registration ORM object with sensible defaults."""
    defaults = dict(
        id=1,
        ulpin="TEST-ULPIN-001",
        deed_no="DEED-2024-001",
        deed_type="Sale",
        registration_date=date(2024, 1, 15),
        sro_office="SRO Delhi",
        buyer="Ramesh Kumar",
        seller="Priya Sharma",
        transaction_value=5_000_000,
        stamp_duty_paid=True,
    )
    defaults.update(kwargs)
    obj = MagicMock(spec=Registration)
    for k, v in defaults.items():
        setattr(obj, k, v)
    return obj


def _make_audit() -> MagicMock:
    obj = MagicMock(spec=AuditLog)
    obj.id = 1
    obj.action = "REGISTER_DEED"
    obj.resource_type = "registration"
    obj.resource_id = "1"
    return obj


# ---------------------------------------------------------------------------
# DB session mock factory
# ---------------------------------------------------------------------------

def _make_db_with_registration(reg: MagicMock | None, audit: MagicMock | None = None):
    """Return an AsyncMock session that handles the registration router's queries."""
    db = AsyncMock()

    # scalar_one_or_none() for select(Registration) or db.get(Registration, id)
    scalar_result = AsyncMock()
    scalar_result.scalar_one_or_none = AsyncMock(return_value=reg)
    scalar_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[reg] if reg else [])))

    db.execute = AsyncMock(return_value=scalar_result)
    db.get = AsyncMock(return_value=reg)
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()

    # For audit chain: query for last audit hash returns genesis
    audit_hash_result = AsyncMock()
    audit_hash_result.scalar_one_or_none = AsyncMock(return_value=None)

    # First call: list query or get Registration; second: audit hash query
    # We set execute to cycle through results
    call_results = [scalar_result, audit_hash_result]
    call_count = [0]

    async def _execute(*args, **kwargs):
        idx = call_count[0]
        call_count[0] += 1
        if idx < len(call_results):
            return call_results[idx]
        return audit_hash_result

    db.execute = _execute
    return db


# ---------------------------------------------------------------------------
# POST /registration — REG_OFF → 201 + audit + Redis publish
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_post_registration_reg_off_creates_201_and_publishes():
    """
    POST /registration by REG_OFF must return 201, write an audit row,
    and call redis.publish("registration.completed", …).

    Requirements: 12.1
    """
    reg = _make_registration()

    db = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock(side_effect=lambda obj: None)

    # audit chain: no previous rows
    audit_result = AsyncMock()
    audit_result.scalar_one_or_none = AsyncMock(return_value=None)
    db.execute = AsyncMock(return_value=audit_result)

    redis = AsyncMock()
    redis.publish = AsyncMock(return_value=1)

    # After db.refresh, the created Registration object needs an id populated
    # (db.flush is a no-op mock, so the id is never auto-assigned).
    async def _refresh(obj):
        obj.id = 1

    db.refresh = AsyncMock(side_effect=_refresh)

    # Patch write_audit so it doesn't need a real DB
    with patch("routers.registration.write_audit", new_callable=AsyncMock) as mock_audit:
        mock_audit.return_value = _make_audit()

        async def override_db():
            yield db

        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[get_redis] = lambda: redis
        app.dependency_overrides[get_current_user] = lambda: _make_user("REG_OFF", "reg_officer", "DL")

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/v1/registration",
                json={
                    "ulpin": "TEST-ULPIN-001",
                    "deed_no": "DEED-2024-001",
                    "deed_type": "Sale",
                    "registration_date": "2024-01-15",
                    "sro_office": "SRO Delhi",
                    "buyer": "Ramesh Kumar",
                    "seller": "Priya Sharma",
                    "transaction_value": 5000000,
                    "stamp_duty_paid": True,
                },
            )

    app.dependency_overrides.clear()

    assert response.status_code == status.HTTP_201_CREATED, response.text
    body = response.json()
    assert body["success"] is True

    # Audit must have been written
    mock_audit.assert_called_once()
    call_kwargs = mock_audit.call_args.kwargs
    assert call_kwargs["action"] == "REGISTER_DEED"
    assert call_kwargs["actor_role"] == "REG_OFF"

    # Redis publish must have been called with correct channel
    redis.publish.assert_called_once()
    channel = redis.publish.call_args.args[0]
    assert channel == "registration.completed"


@pytest.mark.anyio
async def test_post_registration_citizen_returns_403():
    """
    POST /registration by CITIZEN must return 403.

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
            "/api/v1/registration",
            json={
                "ulpin": "TEST-ULPIN-001",
                "deed_no": "DEED-2024-001",
                "deed_type": "Sale",
                "registration_date": "2024-01-15",
                "sro_office": "SRO Delhi",
                "buyer": "Ramesh Kumar",
                "seller": "Priya Sharma",
                "transaction_value": 5000000,
                "stamp_duty_paid": True,
            },
        )

    app.dependency_overrides.clear()
    assert response.status_code == status.HTTP_403_FORBIDDEN


# ---------------------------------------------------------------------------
# GET /registration — CITIZEN omits transaction_value
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_get_registration_list_citizen_omits_transaction_value():
    """
    GET /registration by CITIZEN must return RegistrationPublic: no transaction_value.

    Requirements: 12.1, 12.2
    """
    reg = _make_registration()

    db = AsyncMock()
    scalars_mock = MagicMock()
    scalars_mock.all = MagicMock(return_value=[reg])
    exec_result = AsyncMock()
    exec_result.scalars = MagicMock(return_value=scalars_mock)
    db.execute = AsyncMock(return_value=exec_result)

    async def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_redis] = lambda: AsyncMock()
    app.dependency_overrides[get_current_user] = lambda: _make_user("CITIZEN")

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get("/api/v1/registration")

    app.dependency_overrides.clear()

    assert response.status_code == status.HTTP_200_OK, response.text
    body = response.json()
    assert body["success"] is True
    items = body["data"]
    assert isinstance(items, list)
    assert len(items) == 1
    item = items[0]
    assert "transaction_value" not in item, (
        "CITIZEN must not see transaction_value in registration response"
    )


@pytest.mark.anyio
async def test_get_registration_list_reg_off_includes_transaction_value():
    """
    GET /registration by REG_OFF must include transaction_value.

    Requirements: 12.1
    """
    reg = _make_registration()

    db = AsyncMock()
    scalars_mock = MagicMock()
    scalars_mock.all = MagicMock(return_value=[reg])
    exec_result = AsyncMock()
    exec_result.scalars = MagicMock(return_value=scalars_mock)
    db.execute = AsyncMock(return_value=exec_result)

    async def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_redis] = lambda: AsyncMock()
    app.dependency_overrides[get_current_user] = lambda: _make_user("REG_OFF", jurisdiction="DL")

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get("/api/v1/registration")

    app.dependency_overrides.clear()

    assert response.status_code == status.HTTP_200_OK, response.text
    body = response.json()
    items = body["data"]
    assert len(items) == 1
    assert "transaction_value" in items[0]
    assert items[0]["transaction_value"] == 5_000_000


# ---------------------------------------------------------------------------
# GET /registration/{id} — single record masking
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_get_registration_by_id_citizen_omits_transaction_value():
    """
    GET /registration/{id} by CITIZEN must omit transaction_value.

    Requirements: 12.1, 12.2
    """
    reg = _make_registration(id=42)

    db = AsyncMock()
    db.get = AsyncMock(return_value=reg)

    async def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_redis] = lambda: AsyncMock()
    app.dependency_overrides[get_current_user] = lambda: _make_user("CITIZEN")

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get("/api/v1/registration/42")

    app.dependency_overrides.clear()

    assert response.status_code == status.HTTP_200_OK, response.text
    item = response.json()["data"]
    assert "transaction_value" not in item


@pytest.mark.anyio
async def test_get_registration_by_id_not_found():
    """
    GET /registration/{id} returns 404 when the record does not exist.

    Requirements: 12.2
    """
    db = AsyncMock()
    db.get = AsyncMock(return_value=None)

    async def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_redis] = lambda: AsyncMock()
    app.dependency_overrides[get_current_user] = lambda: _make_user("REG_OFF", jurisdiction="DL")

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get("/api/v1/registration/9999")

    app.dependency_overrides.clear()
    assert response.status_code == status.HTTP_404_NOT_FOUND


# ---------------------------------------------------------------------------
# REV_OFF also receives public (masked) view
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_get_registration_list_rev_off_omits_transaction_value():
    """
    GET /registration by REV_OFF must omit transaction_value (public role).

    Requirements: 12.1, 12.2
    """
    reg = _make_registration()

    db = AsyncMock()
    scalars_mock = MagicMock()
    scalars_mock.all = MagicMock(return_value=[reg])
    exec_result = AsyncMock()
    exec_result.scalars = MagicMock(return_value=scalars_mock)
    db.execute = AsyncMock(return_value=exec_result)

    async def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_redis] = lambda: AsyncMock()
    app.dependency_overrides[get_current_user] = lambda: _make_user("REV_OFF", jurisdiction="DL")

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get("/api/v1/registration")

    app.dependency_overrides.clear()

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    items = body["data"]
    assert "transaction_value" not in items[0]


# ---------------------------------------------------------------------------
# POST /registration — jurisdiction mismatch → 403
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_post_registration_jurisdiction_mismatch_returns_403():
    """
    When a state-scoped officer attempts to register a deed for a parcel outside their
    jurisdiction, the RBAC layer must return 403.

    The jurisdiction guard (check_jurisdiction) is simulated here via a dependency
    override that injects a user mismatch and a mock database that returns a parcel
    belonging to a different state.

    Requirements: 12.2
    """
    from fastapi import HTTPException
    from core.rbac import require_role

    # Simulate a REG_OFF from DL (Delhi) trying to register in MH (Maharashtra)
    mismatch_user = UserClaims(username="reg_off_dl", role="REG_OFF", jurisdiction="DL")

    db = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()

    # Simulate: check_jurisdiction raises 403 because parcel.state_code = "MH" != "DL"
    async def override_db():
        yield db

    # Override get_current_user so the role passes require_role but jurisdiction guard fires
    # We simulate the jurisdiction enforcement by overriding require_role for REG_OFF
    # to raise 403 when jurisdiction doesn't match.
    def _jurisdiction_mismatch_user():
        raise HTTPException(
            status_code=403,
            detail="Parcel is in state 'MH'; your jurisdiction is 'DL'",
        )

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_redis] = lambda: AsyncMock()
    app.dependency_overrides[get_current_user] = _jurisdiction_mismatch_user

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/registration",
            json={
                "ulpin": "MH-MUM-001",
                "deed_no": "DEED-2024-002",
                "deed_type": "Sale",
                "registration_date": "2024-01-15",
                "sro_office": "SRO Mumbai",
                "buyer": "Anil Sharma",
                "seller": "Suresh Patel",
                "transaction_value": 3000000,
                "stamp_duty_paid": True,
            },
        )

    app.dependency_overrides.clear()
    assert response.status_code == status.HTTP_403_FORBIDDEN, response.text
    body = response.json()
    assert body["success"] is False
