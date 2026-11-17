"""
test_token_blacklist.py — Property-based test for token blacklist behaviour.

Property 7: Token blacklist prevents reuse
  For any token that has been successfully submitted to /auth/logout, a subsequent
  request using that token SHALL return HTTP 401 and SHALL NOT proceed to any
  business logic.

Validates: Requirements 4.3, 4.4

The test exercises three tiers of the blacklist implementation:

  1. `blacklist_token` / `is_blacklisted` in isolation — verifies that after
     blacklisting a JTI, `is_blacklisted` reliably returns True across the full
     space of arbitrary JTI strings and TTL values.

  2. `verify_token` with a live (non-blacklisted) token — verifies that the
     function accepts a valid, unexpired token whose JTI is not in the blacklist.

  3. `verify_token` with a blacklisted token — verifies that after the JTI is
     blacklisted, `verify_token` raises `HTTPException(401)` for every call.

All Redis operations use `fakeredis.FakeAsyncRedis` — no live Redis instance is
required.  Async calls are driven via `asyncio.run()` inside synchronous Hypothesis
test bodies, matching the pattern used in `test_audit_chain_property.py`.
"""

from __future__ import annotations

import sys
import os

# Allow importing backend modules directly when pytest runs from project root.
_backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, _backend_dir)

import asyncio
from uuid import uuid4

import fakeredis
import pytest
from fastapi import HTTPException
from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st

from core.auth import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    blacklist_token,
    create_access_token,
    is_blacklisted,
    verify_token,
)

# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

# JTI values are UUIDs in production but the blacklist logic treats them as
# opaque strings.  Generate a broad space of non-empty strings to prove the
# key-formatting logic (``bl:<jti>``) handles arbitrary content correctly.
_jti_strategy = st.text(
    alphabet=st.characters(
        whitelist_categories=("Lu", "Ll", "Nd"),
        whitelist_characters="-_.",
    ),
    min_size=1,
    max_size=128,
)

# TTL in seconds: at least 1 to ensure the key doesn't expire instantly.
# Cap at one day to keep the tests well-behaved.
_ttl_strategy = st.integers(min_value=1, max_value=86_400)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fresh_redis() -> fakeredis.FakeAsyncRedis:
    """Return a fresh isolated FakeAsyncRedis instance per test."""
    return fakeredis.FakeAsyncRedis()


def _make_token(extra: dict | None = None) -> tuple[str, str]:
    """
    Create a valid, signed access token and return ``(token, jti)``.

    ``extra`` is merged into the payload so callers can embed a known JTI.
    """
    jti = str(uuid4())
    payload: dict = {"sub": "test_user", "role": "CITIZEN", "jurisdiction": None}
    if extra:
        payload.update(extra)
    token = create_access_token(payload)
    # Decode jti from the token without full verification (jose exposes it).
    from jose import jwt as _jwt
    from core.auth import JWT_SECRET, JWT_ALGORITHM

    decoded = _jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    return token, decoded["jti"]


# ---------------------------------------------------------------------------
# Property 7a — blacklist_token + is_blacklisted: blacklisted JTI is detected
# ---------------------------------------------------------------------------

@given(jti=_jti_strategy, ttl=_ttl_strategy)
@settings(
    max_examples=100,
    suppress_health_check=[HealthCheck.too_slow],
)
def test_blacklisted_jti_is_detected(jti: str, ttl: int) -> None:
    """
    **Property 7: Token blacklist prevents reuse**
    **Validates: Requirements 4.3, 4.4**

    For any JTI string and TTL, calling ``blacklist_token(jti, ttl, redis)``
    MUST cause ``is_blacklisted(jti, redis)`` to return True immediately after.
    """

    async def _run() -> None:
        redis = _fresh_redis()
        # Before blacklisting, the JTI must not be present.
        assert not await is_blacklisted(jti, redis), (
            f"JTI '{jti}' should not be blacklisted before blacklist_token()"
        )
        await blacklist_token(jti, ttl, redis)
        # After blacklisting, the JTI must be detected.
        assert await is_blacklisted(jti, redis), (
            f"JTI '{jti}' must be blacklisted after blacklist_token()"
        )

    asyncio.run(_run())


# ---------------------------------------------------------------------------
# Property 7b — blacklist isolation: blacklisting one JTI does not affect others
# ---------------------------------------------------------------------------

@given(
    jti_a=_jti_strategy,
    jti_b=_jti_strategy,
    ttl=_ttl_strategy,
)
@settings(
    max_examples=80,
    suppress_health_check=[HealthCheck.too_slow],
)
def test_blacklist_does_not_affect_other_jtis(
    jti_a: str, jti_b: str, ttl: int
) -> None:
    """
    **Property 7: Token blacklist prevents reuse**
    **Validates: Requirements 4.3, 4.4**

    Blacklisting JTI-A MUST NOT cause ``is_blacklisted(jti_b, ...)`` to return
    True when jti_a != jti_b (no cross-contamination between keys).
    """

    async def _run() -> None:
        # Skip if the two JTIs happen to be equal — that case is covered by 7a.
        if jti_a == jti_b:
            return

        redis = _fresh_redis()
        await blacklist_token(jti_a, ttl, redis)

        assert not await is_blacklisted(jti_b, redis), (
            f"Blacklisting JTI '{jti_a}' must not affect JTI '{jti_b}'"
        )

    asyncio.run(_run())


# ---------------------------------------------------------------------------
# Property 7c — verify_token accepts valid token before blacklisting
# ---------------------------------------------------------------------------

def test_verify_token_accepts_non_blacklisted_token() -> None:
    """
    **Property 7: Token blacklist prevents reuse**
    **Validates: Requirements 4.3, 4.4**

    A freshly created access token whose JTI has NOT been blacklisted MUST be
    accepted by ``verify_token`` (no HTTPException raised).
    """

    async def _run() -> None:
        redis = _fresh_redis()
        token, jti = _make_token()
        payload = await verify_token(token, redis)
        assert payload["sub"] == "test_user"
        assert payload["jti"] == jti
        assert payload["type"] == "access"

    asyncio.run(_run())


# ---------------------------------------------------------------------------
# Property 7d — verify_token rejects token after blacklisting
# ---------------------------------------------------------------------------

def test_verify_token_raises_401_for_blacklisted_token() -> None:
    """
    **Property 7: Token blacklist prevents reuse**
    **Validates: Requirements 4.3, 4.4**

    After ``blacklist_token(jti, ...)`` is called, every subsequent call to
    ``verify_token`` with that token MUST raise ``HTTPException`` with status
    code 401.
    """

    async def _run() -> None:
        redis = _fresh_redis()
        token, jti = _make_token()

        # Confirm it works before blacklisting.
        await verify_token(token, redis)

        # Blacklist the JTI (TTL = remaining lifetime of a 15-min access token).
        ttl_seconds = ACCESS_TOKEN_EXPIRE_MINUTES * 60
        await blacklist_token(jti, ttl_seconds, redis)

        # Every subsequent call must be rejected with HTTP 401.
        with pytest.raises(HTTPException) as exc_info:
            await verify_token(token, redis)

        assert exc_info.value.status_code == 401, (
            f"Expected 401, got {exc_info.value.status_code}"
        )

    asyncio.run(_run())


# ---------------------------------------------------------------------------
# Property 7e — verify_token consistently rejects across repeated calls
# ---------------------------------------------------------------------------

@given(n_calls=st.integers(min_value=1, max_value=20))
@settings(
    max_examples=50,
    suppress_health_check=[HealthCheck.too_slow],
)
def test_blacklisted_token_rejected_on_all_subsequent_calls(n_calls: int) -> None:
    """
    **Property 7: Token blacklist prevents reuse**
    **Validates: Requirements 4.3, 4.4**

    After a token is blacklisted, ALL N subsequent calls to ``verify_token``
    with that same token MUST raise ``HTTPException(401)``.  The blacklist
    provides a permanent block for the token's remaining lifetime.
    """

    async def _run() -> None:
        redis = _fresh_redis()
        token, jti = _make_token()

        ttl_seconds = ACCESS_TOKEN_EXPIRE_MINUTES * 60
        await blacklist_token(jti, ttl_seconds, redis)

        for call_index in range(n_calls):
            with pytest.raises(HTTPException) as exc_info:
                await verify_token(token, redis)
            assert exc_info.value.status_code == 401, (
                f"Call {call_index + 1}: expected 401, "
                f"got {exc_info.value.status_code}"
            )

    asyncio.run(_run())
