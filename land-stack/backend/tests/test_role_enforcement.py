"""
test_role_enforcement.py — Property-based test for RBAC role enforcement.

Property 3: Role enforcement — forbidden access
  For any (endpoint, role) pair where role ∉ the endpoint's allowed set,
  the system MUST return HTTP 403 with no DB side-effects.

Validates: Requirements 5.2, 5.3

Strategy
--------
- Build a minimal in-process FastAPI test app with one route per access
  pattern from docs/RBAC_MATRIX.md.
- Each route uses ``require_role([...])`` exactly as production code does.
- Override ``get_current_user`` via dependency override so no live DB / Redis
  is needed.
- Use Hypothesis to generate role strings NOT in the allowed set for a given
  endpoint and assert the response is always HTTP 403.
- Run the client synchronously (``httpx.Client`` with ASGI transport) inside
  a Hypothesis example so the whole test suite stays synchronous—Hypothesis
  does not support async ``@given`` targets without extra plumbing.
"""

from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dataclasses import dataclass
from typing import Callable, Any

import pytest
from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st
from fastapi import Depends, FastAPI, APIRouter
from fastapi.testclient import TestClient  # synchronous ASGI transport

from core.rbac import require_role, get_current_user, UserClaims, VALID_ROLES

# ---------------------------------------------------------------------------
# All 7 valid roles (also the full universe for Hypothesis sampling)
# ---------------------------------------------------------------------------

ALL_ROLES: list[str] = sorted(VALID_ROLES)

# ---------------------------------------------------------------------------
# Representative endpoint definitions (method, path, allowed_roles)
# based on docs/RBAC_MATRIX.md "API Endpoint → Role Mapping"
# ---------------------------------------------------------------------------

ENDPOINT_SPECS: list[tuple[str, str, list[str]]] = [
    # (HTTP method, path suffix, allowed role list)
    ("POST", "/parcels",           ["REV_OFF", "STATE_ADMIN", "NATL_ADMIN"]),
    ("PUT",  "/ror",               ["REV_OFF", "STATE_ADMIN", "NATL_ADMIN"]),
    ("POST", "/registration",      ["REG_OFF", "STATE_ADMIN", "NATL_ADMIN"]),
    ("POST", "/encumbrance",       ["REG_OFF", "STATE_ADMIN", "NATL_ADMIN"]),
    ("PUT",  "/zoning",            ["PLAN_OFF", "STATE_ADMIN", "NATL_ADMIN"]),
    ("POST", "/building-permission", ["PLAN_OFF", "STATE_ADMIN", "NATL_ADMIN"]),
    ("PUT",  "/tax",               ["TAX_OFF", "STATE_ADMIN", "NATL_ADMIN"]),
    ("GET",  "/workflow/tasks",    ["REV_OFF", "REG_OFF", "PLAN_OFF", "TAX_OFF", "STATE_ADMIN", "NATL_ADMIN"]),
    ("POST", "/citizen/service-request", ["CITIZEN"]),
    ("GET",  "/citizen/requests",  ["CITIZEN"]),
    ("POST", "/ml/change-detection", ["PLAN_OFF", "STATE_ADMIN", "NATL_ADMIN"]),
    ("POST", "/ml/fraud-score",    ["REG_OFF", "STATE_ADMIN", "NATL_ADMIN"]),
    ("POST", "/ml/ocr-extract",    ["REV_OFF", "STATE_ADMIN", "NATL_ADMIN"]),
    ("PUT",  "/admin/state-adapter", ["NATL_ADMIN"]),
    ("GET",  "/analytics/national", ["NATL_ADMIN"]),
]

# ---------------------------------------------------------------------------
# Build the test FastAPI application
# ---------------------------------------------------------------------------

def _build_test_app() -> FastAPI:
    """
    Return a minimal FastAPI app that mirrors the RBAC guards from RBAC_MATRIX.md.

    Each route simply returns HTTP 200 when the role is allowed; the
    ``require_role`` dependency raises 403 before the handler body is reached
    when the role is disallowed.
    """
    app = FastAPI()

    for method, path, allowed in ENDPOINT_SPECS:
        # Capture allowed in a closure; each iteration must bind its own copy.
        def _make_handler(roles: list[str]) -> Callable:
            async def _handler(user: UserClaims = Depends(require_role(roles))) -> dict:
                return {"ok": True, "role": user.role}
            return _handler

        router = APIRouter()
        handler = _make_handler(allowed)

        if method == "GET":
            router.get(path)(_make_handler(allowed))
        elif method == "POST":
            router.post(path)(_make_handler(allowed))
        elif method == "PUT":
            router.put(path)(_make_handler(allowed))

        app.include_router(router)

    return app


_test_app = _build_test_app()

# ---------------------------------------------------------------------------
# Dependency override factory
# ---------------------------------------------------------------------------

def _override_get_current_user(role: str) -> Callable:
    """Return a dependency override that injects a UserClaims with *role*."""
    async def _dep() -> UserClaims:
        return UserClaims(username="test_user", role=role, jurisdiction=None)
    return _dep


def _client_for_role(role: str) -> TestClient:
    """Return a TestClient whose JWT always resolves to *role*."""
    app_copy = _test_app  # the test app is stateless — override per request
    app_copy.dependency_overrides[get_current_user] = _override_get_current_user(role)
    return TestClient(app_copy, raise_server_exceptions=True)


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

# Pick a random endpoint index from ENDPOINT_SPECS
_endpoint_idx = st.integers(min_value=0, max_value=len(ENDPOINT_SPECS) - 1)


def _disallowed_role_for(idx: int) -> st.SearchStrategy[str]:
    """Return a strategy that draws a role NOT in the allowed set for endpoint *idx*."""
    allowed = set(ENDPOINT_SPECS[idx][2])
    disallowed = [r for r in ALL_ROLES if r not in allowed]
    if not disallowed:
        # Defensive: every role is allowed → skip by drawing nothing valid here.
        # In practice, no endpoint allows all 7 roles, so this branch never fires.
        return st.nothing()
    return st.sampled_from(disallowed)


# A strategy that yields (endpoint_idx, disallowed_role) pairs.
_forbidden_pair = _endpoint_idx.flatmap(
    lambda idx: st.tuples(st.just(idx), _disallowed_role_for(idx))
)

# ---------------------------------------------------------------------------
# Property 3: Role enforcement — forbidden access
# ---------------------------------------------------------------------------

# Property 3: Role enforcement — forbidden access
@given(pair=_forbidden_pair)
@settings(
    max_examples=200,
    suppress_health_check=[HealthCheck.too_slow],
)
def test_forbidden_role_always_returns_403(pair: tuple[int, str]) -> None:
    """
    **Property 3: Role enforcement — forbidden access**
    **Validates: Requirements 5.2, 5.3**

    For any (endpoint, role) pair where role ∉ the endpoint's allowed set:
    - The HTTP response status MUST be 403 (Forbidden).
    - No DB side-effect can occur because the dependency raises before the
      handler body is reached.
    """
    idx, role = pair
    method, path, allowed = ENDPOINT_SPECS[idx]

    client = _client_for_role(role)

    if method == "GET":
        response = client.get(path)
    elif method == "POST":
        response = client.post(path, json={})
    elif method == "PUT":
        response = client.put(path, json={})
    else:
        raise AssertionError(f"Unhandled method {method!r}")

    assert response.status_code == 403, (
        f"Expected 403 for role={role!r} on {method} {path} "
        f"(allowed={allowed}), got {response.status_code}. "
        f"Body: {response.text}"
    )


# ---------------------------------------------------------------------------
# Complementary property: allowed role returns 200 (not 403)
# ---------------------------------------------------------------------------

# This is NOT part of Property 3 but serves as a correctness anchor:
# if the override were broken the main property would be vacuously true.
@given(idx=_endpoint_idx)
@settings(max_examples=50)
def test_allowed_role_returns_200(idx: int) -> None:
    """
    **Validates: Requirements 5.2**

    For every endpoint, at least one allowed role MUST receive HTTP 200,
    confirming the RBAC guard does not over-block.
    """
    method, path, allowed = ENDPOINT_SPECS[idx]
    # Pick the first allowed role as a representative.
    role = allowed[0]

    client = _client_for_role(role)

    if method == "GET":
        response = client.get(path)
    elif method == "POST":
        response = client.post(path, json={})
    elif method == "PUT":
        response = client.put(path, json={})
    else:
        raise AssertionError(f"Unhandled method {method!r}")

    assert response.status_code == 200, (
        f"Expected 200 for role={role!r} on {method} {path}, "
        f"got {response.status_code}. Body: {response.text}"
    )


# ---------------------------------------------------------------------------
# Unit test: direct require_role logic (no HTTP round-trip)
# ---------------------------------------------------------------------------

import asyncio
from fastapi import HTTPException


def test_require_role_raises_403_for_disallowed_role() -> None:
    """
    **Validates: Requirements 5.3**

    Call the inner _check coroutine produced by require_role() directly and
    assert it raises HTTPException(403) for a disallowed role.

    ``require_role(roles)`` returns a *callable* (the inner ``_check`` async
    function).  Calling it with an explicit ``user=`` argument bypasses
    FastAPI's dependency injection so we can test the logic in isolation.
    """
    allowed = ["REV_OFF", "STATE_ADMIN", "NATL_ADMIN"]
    # require_role returns the inner _check function directly (not a Depends).
    inner_check = require_role(allowed)

    async def _run(role: str) -> None:
        claims = UserClaims(username="u", role=role, jurisdiction=None)
        await inner_check(user=claims)

    # Disallowed role must raise HTTP 403.
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(_run("CITIZEN"))
    assert exc_info.value.status_code == 403

    # Allowed role must NOT raise.
    asyncio.run(_run("REV_OFF"))


def test_require_role_allows_all_roles_in_allowed_list() -> None:
    """
    **Validates: Requirements 5.2**

    Every role explicitly listed in the allowed set must pass require_role
    without raising an exception.
    """
    allowed = ["REG_OFF", "STATE_ADMIN", "NATL_ADMIN"]
    inner_check = require_role(allowed)

    async def _check_role(role: str) -> None:
        claims = UserClaims(username="u", role=role, jurisdiction=None)
        await inner_check(user=claims)

    for role in allowed:
        asyncio.run(_check_role(role))  # must not raise
