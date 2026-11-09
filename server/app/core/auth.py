"""
Clerk JWT validation dependency.

Usage:
    from app.core.auth import get_current_user

    @router.get("/protected")
    async def protected(user: dict = Depends(get_current_user)):
        clerk_user_id = user["sub"]
"""

import time
from typing import Optional

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from app.config.settings import settings

# ---------------------------------------------------------------------------
# JWKS cache
# ---------------------------------------------------------------------------
_jwks_cache: Optional[dict] = None
_jwks_fetched_at: float = 0.0
_JWKS_TTL = 60  # seconds


async def _get_jwks() -> dict:
    """Fetch Clerk's JWKS, caching the result for 60 seconds."""
    global _jwks_cache, _jwks_fetched_at

    now = time.monotonic()
    if _jwks_cache is not None and (now - _jwks_fetched_at) < _JWKS_TTL:
        return _jwks_cache

    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(settings.CLERK_JWKS_URL)
        response.raise_for_status()

    _jwks_cache = response.json()
    _jwks_fetched_at = now
    return _jwks_cache


# ---------------------------------------------------------------------------
# Dependency
# ---------------------------------------------------------------------------
_bearer = HTTPBearer(auto_error=True)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> dict:
    """
    FastAPI dependency that validates a Clerk-issued Bearer JWT.

    Returns the decoded JWT payload. ``payload["sub"]`` is the Clerk user ID.

    Raises HTTP 401 on any validation failure.
    """
    token = credentials.credentials

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # Decode header to get the key ID (kid)
        unverified_header = jwt.get_unverified_header(token)
    except JWTError:
        raise credentials_exception

    jwks = await _get_jwks()

    # Find the matching public key by kid
    matching_key = None
    for key in jwks.get("keys", []):
        if key.get("kid") == unverified_header.get("kid"):
            matching_key = key
            break

    if matching_key is None:
        # kid not found — try refreshing the cache once
        global _jwks_cache
        _jwks_cache = None
        jwks = await _get_jwks()
        for key in jwks.get("keys", []):
            if key.get("kid") == unverified_header.get("kid"):
                matching_key = key
                break

    if matching_key is None:
        raise credentials_exception

    try:
        payload = jwt.decode(
            token,
            matching_key,
            algorithms=["RS256"],
            options={"verify_aud": False},  # Clerk tokens may omit aud
        )
    except JWTError:
        raise credentials_exception

    return payload
