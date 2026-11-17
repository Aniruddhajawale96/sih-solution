"""
tests/test_auth.py — Unit tests for routers/auth.py (login / refresh / logout).

Validates: Requirements 12.1, 12.2

Covers the seven auth contract cases from task 15.1:
  1. POST /auth/login with valid credentials  -> 200, response carries
     access_token, refresh_token, token_type, role, jurisdiction.
  2. POST /auth/login with wrong password     -> 401.
  3. POST /auth/login with unknown username    -> 401.
  4. POST /auth/refresh with a valid refresh    -> 200, new access_token.
  5. POST /auth/logout                          -> 200, both token JTIs are
     blacklisted in Redis.
  6. After logout, any request with the same access token -> 401 (blacklisted).
  7. Expired access token                       -> 401.

Tests use httpx.AsyncClient with FastAPI's ASGI transport — no live PostgreSQL
or Redis.  ``get_db`` is replaced with an AsyncMock; the Redis dependency is
replaced with a tiny in-process ``_FakeRedis`` whose ``set``/``exists`` track
blacklist state, so the real ``blacklist_token`` / ``is_blacklisted`` /
``verify_token`` code paths run end-to-end.  Login tests mock
``verify_password`` (per the task's "Mock verify_password ... where
appropriate" option) to drive the handler's success/failure branches without
bcrypt overhead.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

# Allow importing backend/ modules directly when running pytest from the repo root
_backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

import contextlib

import httpx
import pytest
from jose import jwt as jose_jwt

from core.auth import (
    JWT_ALGORITHM,
    JWT_SECRET,
    create_access_token,
    create_refresh_token,
    is_blacklisted,
)


# ---------------------------------------------------------------------------
# Password check is mocked in login tests (see the task's "Mock verify_password
# ... where appropriate" option) — real bcrypt is not exercised here.
# ---------------------------------------------------------------------------

_FAKE_HASH = "fake-bcrypt-hash"  # placeholder; verify_password is mocked


# ---------------------------------------------------------------------------
# FakeRedis — minimal in-process stand-in for redis.asyncio.Redis
# ---------------------------------------------------------------------------

class _FakeRedis:
    """Track ``set`` calls in a dict so ``exists``/``get`` reflect blacklist state.

    This lets the real ``blacklist_token`` / ``is_blacklisted`` / ``verify_token``
    code paths run against the fake, exercising the actual blacklist logic
    without a live Redis instance.
    """

    def __init__(self) -> None:
        self.store: dict[str, str] = {}

    async def set(self, key: str, value, ex: int | None = None, **kwargs) -> bool:
        self.store[key] = value
        return True

    async def exists(self, key: str) -> int:
        return 1 if key in self.store else 0

    async def get(self, key: str):
        return self.store.get(key)

    async def delete(self, key: str) -> int:
        return 1 if self.store.pop(key, None) is not None else 0

    async def close(self) -> None:
        return None


# ---------------------------------------------------------------------------
# Fake User ORM stub
# ---------------------------------------------------------------------------

class _FakeUser:
    """Stand-in for the User SQLAlchemy model returned from db.execute()."""

    def __init__(
        self,
        username: str = "rev_off1",
        hashed_password: str = _FAKE_HASH,
        role: str = "REV_OFF",
        jurisdiction: str | None = "MH",
        is_active: bool = True,
    ) -> None:
        self.username = username
        self.hashed_password = hashed_password
        self.role = role
        self.jurisdiction = jurisdiction
        self.is_active = is_active


# ---------------------------------------------------------------------------
# AsyncSession mock factories
# ---------------------------------------------------------------------------

def _make_db_override(db_mock):
    """FastAPI dependency override for ``get_db``.

    FastAPI detects async-generator dependencies via ``inspect.isasyncgenfunction``,
    so this must be a real ``async def`` with ``yield``.
    """
    async def _override():
        yield db_mock
    return _override


def _login_db_mock(user: "_FakeUser | None"):
    """AsyncSession mock for the login lookup: ``db.execute(...).scalar_one_or_none()``."""
    db = AsyncMock()
    scalar_result = MagicMock()
    scalar_result.scalar_one_or_none.return_value = user
    db.execute = AsyncMock(return_value=scalar_result)
    return db


def _any_db_mock():
    """Generic AsyncSession mock for endpoints whose DB access never runs
    (because auth fails first).  Keeps ``get_db`` overridden so FastAPI never
    attempts a real database connection."""
    db = AsyncMock()
    scalar_result = MagicMock()
    scalar_result.scalar_one_or_none.return_value = "MH"
    db.execute = AsyncMock(return_value=scalar_result)
    db.get = AsyncMock(return_value=None)
    return db


# ---------------------------------------------------------------------------
# httpx client context manager — wires dependency overrides + ASGI transport
# ---------------------------------------------------------------------------

@contextlib.asynccontextmanager
async def _app_client(db_mock, fake_redis: _FakeRedis):
    from main import app
    from core.database import get_db
    from core.redis_client import get_redis

    app.dependency_overrides[get_db] = _make_db_override(db_mock)
    app.dependency_overrides[get_redis] = lambda: fake_redis
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as ac:
            yield ac
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Token helpers
# ---------------------------------------------------------------------------

def _expired_access_token(role: str = "NATL_ADMIN", jurisdiction: str | None = None) -> str:
    """A signed access token whose ``exp`` is already in the past."""
    payload = {
        "sub": "expired_user",
        "role": role,
        "jurisdiction": jurisdiction,
        "jti": str(uuid4()),
        "type": "access",
        "exp": int((datetime.now(timezone.utc) - timedelta(seconds=10)).timestamp()),
    }
    return jose_jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def _jti_of(token: str) -> str:
    return jose_jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])["jti"]


# ---------------------------------------------------------------------------
# 1. POST /auth/login — valid credentials
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_login_with_valid_credentials_returns_200_and_tokens(anyio_backend):
    """Validates: Requirements 12.1, 12.2 (auth router coverage)."""
    user = _FakeUser(username="rev_off1", role="REV_OFF", jurisdiction="MH")
    db = _login_db_mock(user)
    fake = _FakeRedis()

    # verify_password is mocked so the handler's success branch is exercised
    # without real bcrypt overhead.
    with patch("routers.auth.verify_password", return_value=True):
        async with _app_client(db, fake) as ac:
            resp = await ac.post(
                "/api/v1/auth/login",
                json={"username": "rev_off1", "password": "any-password"},
            )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["success"] is True
    assert body["errors"] == []

    data = body["data"]
    assert data["access_token"]
    assert data["refresh_token"]
    assert data["token_type"] == "bearer"
    assert data["role"] == "REV_OFF"
    assert data["jurisdiction"] == "MH"


# ---------------------------------------------------------------------------
# 2. POST /auth/login — wrong password
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_login_with_wrong_password_returns_401(anyio_backend):
    """Validates: Requirements 12.1, 12.2 — credential failure returns 401."""
    user = _FakeUser(username="rev_off1", role="REV_OFF", jurisdiction="MH")
    db = _login_db_mock(user)
    fake = _FakeRedis()

    # verify_password mocked to fail → handler must raise 401.
    with patch("routers.auth.verify_password", return_value=False):
        async with _app_client(db, fake) as ac:
            resp = await ac.post(
                "/api/v1/auth/login",
                json={"username": "rev_off1", "password": "definitely-wrong"},
            )

    assert resp.status_code == 401, resp.text
    body = resp.json()
    # Envelope present even on error
    assert body["success"] is False
    assert body["data"] is None
    assert body["errors"][0]["code"] == "UNAUTHORIZED"


# ---------------------------------------------------------------------------
# 3. POST /auth/login — unknown username
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_login_with_unknown_username_returns_401(anyio_backend):
    """Validates: Requirements 12.1, 12.2 — unknown user returns 401 (no password check)."""
    db = _login_db_mock(None)  # user lookup returns None
    fake = _FakeRedis()

    async with _app_client(db, fake) as ac:
        resp = await ac.post(
            "/api/v1/auth/login",
            json={"username": "nobody_here", "password": "whatever"},
        )

    assert resp.status_code == 401, resp.text
    body = resp.json()
    assert body["success"] is False
    assert body["errors"][0]["code"] == "UNAUTHORIZED"


# ---------------------------------------------------------------------------
# 4. POST /auth/refresh — valid refresh token yields a new access token
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_refresh_with_valid_refresh_token_returns_new_access_token(anyio_backend):
    """Validates: Requirements 4.2, 12.1, 12.2."""
    refresh_token = create_refresh_token(
        {"sub": "rev_off1", "role": "REV_OFF", "jurisdiction": "MH"}
    )
    db = _any_db_mock()  # refresh does not touch the DB
    fake = _FakeRedis()

    async with _app_client(db, fake) as ac:
        resp = await ac.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["success"] is True

    data = body["data"]
    assert data["access_token"]
    assert data["token_type"] == "bearer"

    # The new access token must be decodable and carry an "access" type claim.
    new_payload = jose_jwt.decode(
        data["access_token"], JWT_SECRET, algorithms=[JWT_ALGORITHM]
    )
    assert new_payload["type"] == "access"
    assert new_payload["sub"] == "rev_off1"


# ---------------------------------------------------------------------------
# 5. POST /auth/logout — both token JTIs blacklisted in Redis
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_logout_blacklists_both_tokens_in_redis(anyio_backend):
    """Validates: Requirements 4.3, 12.1, 12.2."""
    claims = {"sub": "natl_admin1", "role": "NATL_ADMIN", "jurisdiction": None}
    access_token = create_access_token(claims)
    refresh_token = create_refresh_token(claims)
    access_jti = _jti_of(access_token)
    refresh_jti = _jti_of(refresh_token)

    db = _any_db_mock()
    fake = _FakeRedis()

    async with _app_client(db, fake) as ac:
        resp = await ac.post(
            "/api/v1/auth/logout",
            json={"refresh_token": refresh_token},
            headers={"Authorization": f"Bearer {access_token}"},
        )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["success"] is True

    # Both JTIs are now blacklisted in the (fake) Redis.
    assert await is_blacklisted(access_jti, fake) is True
    assert await is_blacklisted(refresh_jti, fake) is True


# ---------------------------------------------------------------------------
# 6. After logout, a request with the same access token is rejected (401)
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_request_after_logout_returns_401(anyio_backend):
    """Validates: Requirements 4.3, 4.4, 12.1, 12.2 — blacklisted token cannot be reused."""
    claims = {"sub": "natl_admin1", "role": "NATL_ADMIN", "jurisdiction": None}
    access_token = create_access_token(claims)
    refresh_token = create_refresh_token(claims)

    db = _any_db_mock()
    fake = _FakeRedis()

    async with _app_client(db, fake) as ac:
        # 1) Log out — blacklists the access token's JTI in the same FakeRedis.
        logout_resp = await ac.post(
            "/api/v1/auth/logout",
            json={"refresh_token": refresh_token},
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert logout_resp.status_code == 200

        # 2) Any subsequent request carrying the now-blacklisted access token
        #    must be rejected with 401 before reaching business logic.
        resp = await ac.get(
            "/api/v1/parcels/MH-MUM-001",
            headers={"Authorization": f"Bearer {access_token}"},
        )

    assert resp.status_code == 401, resp.text
    body = resp.json()
    assert body["success"] is False
    assert body["errors"][0]["code"] == "UNAUTHORIZED"


# ---------------------------------------------------------------------------
# 7. Expired access token -> 401
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_expired_access_token_returns_401(anyio_backend):
    """Validates: Requirements 4.4, 12.1, 12.2 — expired token is rejected."""
    expired_token = _expired_access_token(role="NATL_ADMIN", jurisdiction=None)

    db = _any_db_mock()
    fake = _FakeRedis()

    async with _app_client(db, fake) as ac:
        resp = await ac.get(
            "/api/v1/parcels/MH-MUM-001",
            headers={"Authorization": f"Bearer {expired_token}"},
        )

    assert resp.status_code == 401, resp.text
    body = resp.json()
    assert body["success"] is False
    assert body["errors"][0]["code"] == "UNAUTHORIZED"
