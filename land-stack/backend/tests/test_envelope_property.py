"""
test_envelope_property.py — Property-based tests for the response envelope invariant.

Property 4: Response envelope invariant
Validates: Requirements 1.2

For any value passed through ok() or err(), the serialized response body SHALL be a
valid JSON object containing:
  - "success": bool
  - "data":    any value (or null)
  - "errors":  list

These tests exercise the Envelope[T] schema directly (no live server required).
They use Hypothesis to generate arbitrary Python values and verify the invariant holds
across the full input space.
"""

from __future__ import annotations

import sys
import os

# Allow importing from backend/ root when running pytest from project root.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json
from typing import Any

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from core.schemas import Envelope, ErrorDetail, ok, err

# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

# Generate arbitrary JSON-serialisable scalar values for the data payload.
_json_scalar = st.one_of(
    st.none(),
    st.booleans(),
    st.integers(min_value=-(2**31), max_value=2**31 - 1),
    st.floats(allow_nan=False, allow_infinity=False),
    st.text(max_size=100),
)

# Generate arbitrary JSON-serialisable dicts (one level deep is sufficient).
_json_dict = st.dictionaries(
    keys=st.text(min_size=1, max_size=20),
    values=_json_scalar,
    max_size=5,
)

# Any payload: scalars, dicts, or lists of either.
_arbitrary_data = st.one_of(
    _json_scalar,
    _json_dict,
    st.lists(_json_scalar, max_size=5),
)

# Valid error codes: non-empty uppercase-ish strings.
_error_code = st.text(alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ_", min_size=1, max_size=30)

# Optional field path strings.
_field = st.one_of(st.none(), st.text(min_size=1, max_size=50))


# ---------------------------------------------------------------------------
# Helper assertions
# ---------------------------------------------------------------------------

def _assert_envelope_invariant(body: dict[str, Any]) -> None:
    """Assert every required key is present with the correct type."""
    assert "success" in body, "Envelope missing 'success' key"
    assert "data" in body, "Envelope missing 'data' key"
    assert "errors" in body, "Envelope missing 'errors' key"
    assert isinstance(body["success"], bool), f"'success' must be bool, got {type(body['success'])}"
    assert isinstance(body["errors"], list), f"'errors' must be list, got {type(body['errors'])}"


# ---------------------------------------------------------------------------
# Property tests
# ---------------------------------------------------------------------------

# Property 4: Response envelope invariant — ok() helper
@given(data=_arbitrary_data)
@settings(max_examples=200)
def test_ok_envelope_always_has_required_keys(data: Any) -> None:
    """
    **Validates: Requirements 1.2**

    For any value passed to ok(), model_dump() MUST produce a dict with
    keys 'success' (True), 'data', and 'errors' (empty list).
    """
    envelope = ok(data)
    body = envelope.model_dump()

    _assert_envelope_invariant(body)
    assert body["success"] is True, "ok() envelope must have success=True"
    assert body["errors"] == [], "ok() envelope must have empty errors list"


# Property 4: Response envelope invariant — err() helper
@given(
    code=_error_code,
    message=st.text(max_size=200),
    field=_field,
)
@settings(max_examples=200)
def test_err_envelope_always_has_required_keys(code: str, message: str, field: str | None) -> None:
    """
    **Validates: Requirements 1.2**

    For any (code, message, field) passed to err(), model_dump() MUST produce a
    dict with keys 'success' (False), 'data' (None), and 'errors' (non-empty list).
    """
    envelope = err(code=code, message=message, field=field)
    body = envelope.model_dump()

    _assert_envelope_invariant(body)
    assert body["success"] is False, "err() envelope must have success=False"
    assert body["data"] is None, "err() envelope must have data=None"
    assert len(body["errors"]) == 1, "err() envelope must contain exactly one error"

    error_item = body["errors"][0]
    assert "code" in error_item, "Error detail missing 'code'"
    assert "message" in error_item, "Error detail missing 'message'"
    assert error_item["code"] == code
    assert error_item["message"] == message
    assert error_item.get("field") == field


# Property 4: Response envelope invariant — JSON round-trip
@given(data=_arbitrary_data)
@settings(max_examples=100)
def test_ok_envelope_survives_json_round_trip(data: Any) -> None:
    """
    **Validates: Requirements 1.2**

    The envelope must remain valid after JSON serialisation and deserialisation,
    matching the wire format a client actually receives.
    """
    envelope = ok(data)
    wire = json.dumps(envelope.model_dump())
    parsed = json.loads(wire)

    _assert_envelope_invariant(parsed)
    assert parsed["success"] is True
    assert parsed["errors"] == []


@given(
    code=_error_code,
    message=st.text(max_size=200),
)
@settings(max_examples=100)
def test_err_envelope_survives_json_round_trip(code: str, message: str) -> None:
    """
    **Validates: Requirements 1.2**

    Error envelopes must remain valid after JSON round-trip.
    """
    envelope = err(code=code, message=message)
    wire = json.dumps(envelope.model_dump())
    parsed = json.loads(wire)

    _assert_envelope_invariant(parsed)
    assert parsed["success"] is False
    assert parsed["data"] is None


# ---------------------------------------------------------------------------
# Structural property: Envelope constructed directly also upholds invariant
# ---------------------------------------------------------------------------

@given(
    success=st.booleans(),
    data=_arbitrary_data,
    errors=st.lists(
        st.builds(
            ErrorDetail,
            code=_error_code,
            message=st.text(max_size=100),
            field=_field,
        ),
        max_size=3,
    ),
)
@settings(max_examples=150)
def test_direct_envelope_construction_upholds_invariant(
    success: bool,
    data: Any,
    errors: list[ErrorDetail],
) -> None:
    """
    **Validates: Requirements 1.2**

    Directly constructed Envelope instances (bypassing helpers) must also satisfy
    the invariant — covering any code path that builds Envelope without ok()/err().
    """
    envelope = Envelope(success=success, data=data, errors=errors)
    body = envelope.model_dump()
    _assert_envelope_invariant(body)
