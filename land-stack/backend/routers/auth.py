"""
routers/auth.py — Authentication endpoints.

POST /auth/login    — verify credentials; return access + refresh tokens
POST /auth/refresh  — issue a new access token from a valid refresh token
POST /auth/logout   — blacklist both tokens' JTIs in Redis

All responses are wrapped in the Envelope[T] schema: success paths return
``ok(data)`` directly; failure paths raise ``HTTPException`` whose status code
and detail the global exception handler (main.py) converts into an Envelope
with the matching HTTP status (e.g. 401 → code "UNAUTHORIZED").
Requirements: 4.1, 4.2, 4.3
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import redis.asyncio as aioredis

from core.auth import (
    JWT_ALGORITHM,
    JWT_SECRET,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    blacklist_token,
    create_access_token,
    create_refresh_token,
    verify_password,
    verify_token,
)
from core.database import get_db
from core.redis_client import get_redis
from core.rbac import get_current_user, oauth2_scheme
from core.schemas import Envelope, ok
from core.response_schemas import LoginRequest, LoginResponse, RefreshRequest, RefreshResponse
from models.users import User

router = APIRouter()


# ---------------------------------------------------------------------------
# POST /auth/login
# ---------------------------------------------------------------------------

@router.post(
    "/login",
    response_model=Envelope[LoginResponse],
    status_code=status.HTTP_200_OK,
    summary="Login and obtain JWT tokens",
)
async def login(
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> Envelope[LoginResponse]:
    """
    Verify username/password and return an access token + refresh token.

    - Access token expires in 15 minutes.
    - Refresh token expires in 7 days.
    - Both tokens carry `sub`, `role`, `jurisdiction`, `jti` claims.
    """
    result = await db.execute(select(User).where(User.username == body.username))
    user: User | None = result.scalar_one_or_none()

    if user is None or not verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled",
        )

    token_data = {
        "sub": user.username,
        "role": user.role,
        "jurisdiction": user.jurisdiction,
    }
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    return ok(
        LoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            role=user.role,
            jurisdiction=user.jurisdiction,
        )
    )


# ---------------------------------------------------------------------------
# POST /auth/refresh
# ---------------------------------------------------------------------------

@router.post(
    "/refresh",
    response_model=Envelope[RefreshResponse],
    status_code=status.HTTP_200_OK,
    summary="Refresh access token",
)
async def refresh(
    body: RefreshRequest,
    redis: aioredis.Redis = Depends(get_redis),
) -> Envelope[RefreshResponse]:
    """
    Accept a valid refresh token and issue a new access token.

    Raises 401 if the refresh token is expired, invalid, blacklisted, or is
    not of type "refresh".
    """
    # verify_token raises HTTPException(401) when the refresh token is invalid,
    # expired, or blacklisted. The global handler (main.http_exception_handler)
    # converts that into an Envelope with the correct HTTP status, preserving
    # the "envelope on every response" contract.
    payload = await verify_token(body.refresh_token, redis)

    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Provided token is not a refresh token",
        )

    token_data = {
        "sub": payload.get("sub"),
        "role": payload.get("role"),
        "jurisdiction": payload.get("jurisdiction"),
    }
    new_access_token = create_access_token(token_data)

    return ok(RefreshResponse(access_token=new_access_token, token_type="bearer"))


# ---------------------------------------------------------------------------
# POST /auth/logout
# ---------------------------------------------------------------------------

@router.post(
    "/logout",
    response_model=Envelope[dict],
    status_code=status.HTTP_200_OK,
    summary="Logout — blacklist tokens",
)
async def logout(
    body: RefreshRequest,
    access_token: str = Depends(oauth2_scheme),
    redis: aioredis.Redis = Depends(get_redis),
) -> Envelope[dict]:
    """
    Blacklist both the current access token and the provided refresh token.

    The client must supply:
    - The Bearer access token in the `Authorization` header.
    - The refresh token in the request body `{ "refresh_token": "..." }`.

    Both tokens' JTIs are stored in Redis with a TTL equal to their remaining
    lifetime so that the keys auto-expire and don't pile up indefinitely.
    """
    now = datetime.now(timezone.utc)
    blacklisted = 0

    # Blacklist the access token
    try:
        access_payload = jwt.decode(access_token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        access_jti: str | None = access_payload.get("jti")
        access_exp: int | None = access_payload.get("exp")
        if access_jti and access_exp:
            ttl = max(1, access_exp - int(now.timestamp()))
            await blacklist_token(access_jti, ttl, redis)
            blacklisted += 1
    except JWTError:
        # Access token already expired or malformed — not an error from the client's
        # perspective; we simply cannot blacklist what we cannot parse.
        pass

    # Blacklist the refresh token
    try:
        refresh_payload = jwt.decode(body.refresh_token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        refresh_jti: str | None = refresh_payload.get("jti")
        refresh_exp: int | None = refresh_payload.get("exp")
        if refresh_jti and refresh_exp:
            ttl = max(1, refresh_exp - int(now.timestamp()))
            await blacklist_token(refresh_jti, ttl, redis)
            blacklisted += 1
    except JWTError:
        pass

    return ok({"detail": f"Logged out. {blacklisted} token(s) blacklisted."})
