"""
core/auth.py — JWT token creation/verification, password hashing, and Redis token blacklist.

Token payload structure:
  { sub: username, role: role_code, jurisdiction: state_code|null, jti: uuid4, type: "access"|"refresh" }

Environment variables:
  JWT_SECRET  — signing secret (default: "devsecret-change-in-prod")
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

import redis.asyncio as aioredis
from fastapi import HTTPException, status
from jose import JWTError, jwt
from passlib.context import CryptContext

JWT_SECRET: str = os.getenv("JWT_SECRET", "devsecret-change-in-prod")
JWT_ALGORITHM: str = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
REFRESH_TOKEN_EXPIRE_DAYS: int = 7

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ── Password helpers ──────────────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    """Hash a plaintext password using bcrypt."""
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if *plain* matches the bcrypt *hashed* password."""
    return pwd_context.verify(plain, hashed)


# ── Token creation ────────────────────────────────────────────────────────────

def create_access_token(data: dict[str, Any]) -> str:
    """
    Return a signed HS256 JWT access token.

    The token expires in ACCESS_TOKEN_EXPIRE_MINUTES minutes.
    A unique *jti* (JWT ID) is injected so individual tokens can be blacklisted.
    """
    payload = data.copy()
    payload["exp"] = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload["jti"] = str(uuid4())
    payload["type"] = "access"
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def create_refresh_token(data: dict[str, Any]) -> str:
    """
    Return a signed HS256 JWT refresh token.

    The token expires in REFRESH_TOKEN_EXPIRE_DAYS days.
    """
    payload = data.copy()
    payload["exp"] = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    payload["jti"] = str(uuid4())
    payload["type"] = "refresh"
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


# ── Token verification ────────────────────────────────────────────────────────

async def verify_token(token: str, redis_client: aioredis.Redis) -> dict[str, Any]:
    """
    Decode and validate *token*.

    Raises HTTPException(401) if the token is:
    - expired or cryptographically invalid
    - present on the Redis blacklist (i.e. logged out)
    """
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    jti: str | None = payload.get("jti")
    if jti and await is_blacklisted(jti, redis_client):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked",
        )

    return payload


# ── Blacklist (Redis) ─────────────────────────────────────────────────────────

async def blacklist_token(
    jti: str,
    ttl_seconds: int,
    redis_client: aioredis.Redis,
) -> None:
    """
    Add *jti* to the Redis blacklist with a TTL matching the token's remaining lifetime.

    Key format: ``bl:<jti>``
    """
    await redis_client.set(f"bl:{jti}", "1", ex=ttl_seconds)


async def is_blacklisted(jti: str, redis_client: aioredis.Redis) -> bool:
    """Return True if *jti* appears in the Redis blacklist."""
    return bool(await redis_client.exists(f"bl:{jti}"))
