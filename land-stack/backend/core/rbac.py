"""
core/rbac.py — RBAC dependency factory and jurisdiction guard.

Provides three FastAPI dependencies:
  - get_current_user  : decode JWT → UserClaims dataclass
  - require_role      : dependency factory that enforces an allowed-roles list
  - check_jurisdiction: guard that rejects state-scoped officers whose
                        jurisdiction does not match the target parcel's state_code

Usage in a router::

    @router.get("/{ulpin}")
    async def get_parcel(
        ulpin: str,
        user: UserClaims = Depends(require_role(["REV_OFF", "NATL_ADMIN"])),
        _jc: None = Depends(check_jurisdiction),
    ):
        ...
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import redis.asyncio as aioredis
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.database import get_db
from core.auth import verify_token
from core.redis_client import get_redis

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

VALID_ROLES = {
    "CITIZEN", "REV_OFF", "REG_OFF", "PLAN_OFF",
    "TAX_OFF", "STATE_ADMIN", "NATL_ADMIN",
}

# Roles that are NOT restricted to a single jurisdiction
GLOBAL_ROLES = {"CITIZEN", "NATL_ADMIN"}


@dataclass
class UserClaims:
    """Decoded, validated JWT claims attached to every authenticated request."""

    username: str
    role: str
    jurisdiction: str | None  # state_code for state-scoped roles; None for CITIZEN/NATL_ADMIN


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    redis: aioredis.Redis = Depends(get_redis),
) -> UserClaims:
    """
    Decode the bearer token, check the blacklist, and return a UserClaims instance.

    Raises HTTP 401 if the token is invalid, expired, or blacklisted.
    Raises HTTP 401 if the payload is missing required claims or carries an unknown role.
    """
    payload = await verify_token(token, redis)
    username: str | None = payload.get("sub")
    role: str | None = payload.get("role")
    jurisdiction: str | None = payload.get("jurisdiction")  # may legitimately be None

    if not username or role not in VALID_ROLES:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token claims",
        )
    return UserClaims(username=username, role=role, jurisdiction=jurisdiction)


def require_role(roles: list[str]) -> Callable:
    """
    Dependency factory that restricts a route to the given role codes.

    Usage::

        Depends(require_role(["REV_OFF", "STATE_ADMIN", "NATL_ADMIN"]))

    Returns the authenticated UserClaims so the handler can read it directly.
    Raises HTTP 403 if the caller's role is not in *roles*.
    """
    async def _check(user: UserClaims = Depends(get_current_user)) -> UserClaims:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role {user.role!r} is not allowed. Required: {roles}",
            )
        return user

    return _check


async def check_jurisdiction(
    ulpin: str,
    user: UserClaims = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    For state-scoped roles, verify that the target parcel belongs to the officer's jurisdiction.

    - NATL_ADMIN and CITIZEN always pass (global access).
    - Any other role with ``jurisdiction=None`` also passes (misconfigured token is
      treated permissively here; auth.py would have already rejected a structurally
      invalid token).
    - Raises HTTP 404 if the parcel does not exist.
    - Raises HTTP 403 if ``parcel.state_code != user.jurisdiction``.
    """
    if user.role in GLOBAL_ROLES or user.jurisdiction is None:
        return

    # Lazy import to avoid a circular dependency at module load time.
    from models.parcel import Parcel  # noqa: PLC0415

    result = await db.execute(select(Parcel.state_code).where(Parcel.ulpin == ulpin))
    parcel_state: str | None = result.scalar_one_or_none()

    if parcel_state is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Parcel {ulpin!r} not found",
        )

    if parcel_state != user.jurisdiction:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"Parcel is in state {parcel_state!r}; "
                f"your jurisdiction is {user.jurisdiction!r}"
            ),
        )
