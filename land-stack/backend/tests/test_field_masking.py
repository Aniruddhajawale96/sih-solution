"""
test_field_masking.py — Property-based tests for CITIZEN field masking.

Property 5: Field masking — CITIZEN never receives hidden fields
Validates: Requirements 7.2, 7.4, 7.5

For any resource instance, when serialized with its Public schema, the following
fields MUST be absent from the output:
  - transaction_value        (RegistrationPublic)
  - owner_id_ref             (RorPublic — there is no owner_id_ref field exposed)
  - hash                     (AuditLogPublic)
  - prev_hash                (AuditLogPublic)
  - actor_user               (AuditLogPublic)
  - annual_tax               (TaxPublic)
  - geom / full polygon      (ParcelPublic)
  - hashed_password          (UserInternal — never in any public schema)

Tests operate purely at the Pydantic schema-serialization layer: no live database,
no HTTP server, no FastAPI app required.  Hypothesis generates arbitrary valid
instances and asserts the masking invariants hold across the full input space.
"""

from __future__ import annotations

import sys
import os

# Allow importing backend/ modules when running pytest from project root.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from datetime import date, datetime

import pytest
from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st

from core.response_schemas import (
    AuditLogPublic,
    AuditLogInternal,
    ParcelPublic,
    ParcelInternal,
    RegistrationPublic,
    RegistrationInternal,
    RorPublic,
    TaxPublic,
    TaxInternal,
)

# ---------------------------------------------------------------------------
# Shared text strategies
# ---------------------------------------------------------------------------

_text = st.text(
    alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd", "Zs")),
    min_size=1,
    max_size=50,
)
_ulpin = st.from_regex(r"[A-Z]{2}-[A-Z]{2}-\d{6}", fullmatch=True)
_date = st.dates(min_value=date(2000, 1, 1), max_value=date(2030, 12, 31))
_datetime = st.datetimes(
    min_value=datetime(2000, 1, 1),
    max_value=datetime(2030, 12, 31),
)
_positive_int = st.integers(min_value=1, max_value=10_000_000)
_positive_float = st.floats(min_value=0.01, max_value=100.0, allow_nan=False, allow_infinity=False)
_bool = st.booleans()


# ---------------------------------------------------------------------------
# Helper: collect all keys from a serialized Pydantic model
# ---------------------------------------------------------------------------

def _keys(model) -> set[str]:
    """Return the top-level keys present in model_dump()."""
    return set(model.model_dump().keys())


# ---------------------------------------------------------------------------
# Strategies for each schema
# ---------------------------------------------------------------------------

_audit_log_public_strategy = st.builds(
    AuditLogPublic,
    actor_role=st.sampled_from(
        ["REV_OFF", "REG_OFF", "TAX_OFF", "PLAN_OFF", "STATE_ADMIN", "NATL_ADMIN", "CITIZEN"]
    ),
    action=st.sampled_from(
        [
            "CREATE_PARCEL",
            "UPDATE_ROR",
            "REGISTER_DEED",
            "CREATE_ENCUMBRANCE",
            "UPDATE_ZONING",
            "REASSESS_TAX",
            "ML_FRAUD_SCORE",
            "ML_CHANGE_DETECTION",
            "ML_OCR_EXTRACT",
            "CITIZEN_SERVICE_REQUEST",
        ]
    ),
    resource_type=st.sampled_from(
        ["parcel", "ror", "registration", "encumbrance", "zoning", "tax", "audit_log"]
    ),
    resource_id=_text,
    timestamp=_datetime,
)

_parcel_public_strategy = st.builds(
    ParcelPublic,
    ulpin=_ulpin,
    state_code=st.sampled_from(["CH", "TN", "MH", "UP", "KA"]),
    district=_text,
    village_or_city=_text,
    area_sqm=_positive_float,
    survey_or_khasra_no=_text,
)

_registration_public_strategy = st.builds(
    RegistrationPublic,
    id=_positive_int,
    ulpin=_ulpin,
    deed_no=_text,
    deed_type=st.sampled_from(["SALE", "GIFT", "MORTGAGE", "LEASE", "EXCHANGE"]),
    registration_date=_date,
    sro_office=_text,
    buyer=_text,
    seller=_text,
    stamp_duty_paid=_bool,
)

_ror_public_strategy = st.builds(
    RorPublic,
    ulpin=_ulpin,
    owner_name=_text,
    tenure_type=st.sampled_from(["FREEHOLD", "LEASEHOLD", "GOVERNMENT"]),
    khatauni_no=_text,
    land_use_type=st.sampled_from(["RESIDENTIAL", "COMMERCIAL", "AGRICULTURAL", "INDUSTRIAL"]),
    mutation_status=st.sampled_from(["PENDING", "APPROVED", "REJECTED", "NONE"]),
    last_updated=_date,
)

_tax_public_strategy = st.builds(
    TaxPublic,
    ulpin=_ulpin,
    assessment_id=_text,
    payment_status=st.sampled_from(["PAID", "PENDING", "DEFAULTED"]),
    arrears=st.integers(min_value=0, max_value=1_000_000),
    last_paid_date=st.one_of(st.none(), _date),
)


# ---------------------------------------------------------------------------
# Property 5: AuditLogPublic — hash, prev_hash, actor_user absent
# ---------------------------------------------------------------------------

# Property 5: Field masking — CITIZEN never receives hidden fields
@given(entry=_audit_log_public_strategy)
@settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
def test_audit_log_public_hides_hash_fields(entry: AuditLogPublic) -> None:
    """
    **Property 5: Field masking — CITIZEN never receives hidden fields**
    **Validates: Requirements 7.2, 7.4, 7.5**

    AuditLogPublic MUST NOT expose `hash`, `prev_hash`, or `actor_user`
    in its serialized output — these are sensitive chain fields visible
    only to officer/admin callers via AuditLogInternal.
    """
    keys = _keys(entry)
    assert "hash" not in keys, (
        f"AuditLogPublic exposed 'hash' — citizens must not see chain hashes. "
        f"Keys present: {keys}"
    )
    assert "prev_hash" not in keys, (
        f"AuditLogPublic exposed 'prev_hash' — citizens must not see chain hashes. "
        f"Keys present: {keys}"
    )
    assert "actor_user" not in keys, (
        f"AuditLogPublic exposed 'actor_user' — citizens must not see actor identity. "
        f"Keys present: {keys}"
    )


# Property 5: Field masking — CITIZEN never receives hidden fields
@given(entry=_audit_log_public_strategy)
@settings(max_examples=100)
def test_audit_log_public_includes_required_fields(entry: AuditLogPublic) -> None:
    """
    **Validates: Requirements 7.2**

    AuditLogPublic MUST still expose the non-sensitive fields:
    `actor_role`, `action`, `resource_type`, `resource_id`, `timestamp`.
    """
    keys = _keys(entry)
    for required in ("actor_role", "action", "resource_type", "resource_id", "timestamp"):
        assert required in keys, (
            f"AuditLogPublic missing required public field '{required}'. Keys: {keys}"
        )


# ---------------------------------------------------------------------------
# Property 5: ParcelPublic — full polygon geometry absent
# ---------------------------------------------------------------------------

# Property 5: Field masking — CITIZEN never receives hidden fields
@given(parcel=_parcel_public_strategy)
@settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
def test_parcel_public_hides_full_polygon(parcel: ParcelPublic) -> None:
    """
    **Property 5: Field masking — CITIZEN never receives hidden fields**
    **Validates: Requirements 7.5**

    ParcelPublic MUST NOT expose the `geom` field (full GeoJSON polygon).
    Citizens receive only the centroid + area_sqm, not the full spatial geometry.
    """
    keys = _keys(parcel)
    assert "geom" not in keys, (
        f"ParcelPublic exposed 'geom' (full polygon) — citizens must not "
        f"receive raw geometry. Keys present: {keys}"
    )


# Property 5: Field masking — CITIZEN never receives hidden fields
@given(parcel=_parcel_public_strategy)
@settings(max_examples=100)
def test_parcel_public_includes_area_fields(parcel: ParcelPublic) -> None:
    """
    **Validates: Requirements 7.5**

    ParcelPublic MUST still expose `area_sqm` and location fields so citizens
    can understand the size and location of the parcel without the raw polygon.
    """
    keys = _keys(parcel)
    for required in ("ulpin", "state_code", "district", "village_or_city", "area_sqm",
                     "survey_or_khasra_no"):
        assert required in keys, (
            f"ParcelPublic missing public field '{required}'. Keys: {keys}"
        )


# ---------------------------------------------------------------------------
# Property 5: RegistrationPublic — transaction_value absent
# ---------------------------------------------------------------------------

# Property 5: Field masking — CITIZEN never receives hidden fields
@given(reg=_registration_public_strategy)
@settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
def test_registration_public_hides_transaction_value(reg: RegistrationPublic) -> None:
    """
    **Property 5: Field masking — CITIZEN never receives hidden fields**
    **Validates: Requirements 7.2, 7.4**

    RegistrationPublic MUST NOT expose `transaction_value`.
    Financial transaction amounts are hidden from citizens per RBAC_MATRIX.md.
    """
    keys = _keys(reg)
    assert "transaction_value" not in keys, (
        f"RegistrationPublic exposed 'transaction_value' — this is a hidden field "
        f"for CITIZEN callers. Keys present: {keys}"
    )


# Property 5: Field masking — CITIZEN never receives hidden fields
@given(reg=_registration_public_strategy)
@settings(max_examples=100)
def test_registration_public_includes_deed_fields(reg: RegistrationPublic) -> None:
    """
    **Validates: Requirements 7.2**

    RegistrationPublic MUST still expose deed metadata:
    `deed_no`, `deed_type`, `registration_date`, `sro_office`, `stamp_duty_paid`.
    """
    keys = _keys(reg)
    for required in ("id", "ulpin", "deed_no", "deed_type", "registration_date",
                     "sro_office", "stamp_duty_paid"):
        assert required in keys, (
            f"RegistrationPublic missing public field '{required}'. Keys: {keys}"
        )


# ---------------------------------------------------------------------------
# Property 5: RorPublic — owner_id_ref absent (no such public field)
# ---------------------------------------------------------------------------

# Property 5: Field masking — CITIZEN never receives hidden fields
@given(ror=_ror_public_strategy)
@settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
def test_ror_public_hides_owner_id_ref(ror: RorPublic) -> None:
    """
    **Property 5: Field masking — CITIZEN never receives hidden fields**
    **Validates: Requirements 7.2**

    RorPublic MUST NOT expose `owner_id_ref` (the internal identity reference
    linking the owner to a PAN/Aadhaar-type identifier).  Only the partially
    masked `owner_name` is shown publicly.
    """
    keys = _keys(ror)
    assert "owner_id_ref" not in keys, (
        f"RorPublic exposed 'owner_id_ref' — owner identity reference must be "
        f"hidden from CITIZEN callers. Keys present: {keys}"
    )


# ---------------------------------------------------------------------------
# Property 5: TaxPublic — annual_tax absent
# ---------------------------------------------------------------------------

# Property 5: Field masking — CITIZEN never receives hidden fields
@given(tax=_tax_public_strategy)
@settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
def test_tax_public_hides_annual_tax(tax: TaxPublic) -> None:
    """
    **Property 5: Field masking — CITIZEN never receives hidden fields**
    **Validates: Requirements 7.2**

    TaxPublic MUST NOT expose `annual_tax`.
    Citizens can see arrears and payment_status (public interest), but
    the assessed annual tax amount is restricted to TAX_OFF and above.
    """
    keys = _keys(tax)
    assert "annual_tax" not in keys, (
        f"TaxPublic exposed 'annual_tax' — this is a hidden field for CITIZEN "
        f"callers. Keys present: {keys}"
    )


# Property 5: Field masking — CITIZEN never receives hidden fields
@given(tax=_tax_public_strategy)
@settings(max_examples=100)
def test_tax_public_includes_payment_status(tax: TaxPublic) -> None:
    """
    **Validates: Requirements 7.2**

    TaxPublic MUST still expose `arrears` and `payment_status` — these are
    public-interest fields (defaulter transparency).
    """
    keys = _keys(tax)
    for required in ("ulpin", "assessment_id", "payment_status", "arrears"):
        assert required in keys, (
            f"TaxPublic missing public field '{required}'. Keys: {keys}"
        )


# ---------------------------------------------------------------------------
# Cross-schema: Internal schemas DO contain the fields hidden in Public
# ---------------------------------------------------------------------------

@given(
    actor_role=st.sampled_from(["REV_OFF", "STATE_ADMIN", "NATL_ADMIN"]),
    action=st.sampled_from(["REGISTER_DEED", "UPDATE_ROR", "REASSESS_TAX"]),
    resource_type=st.sampled_from(["registration", "ror", "tax"]),
    resource_id=_text,
    timestamp=_datetime,
    actor_user=_text,
    hash_val=st.from_regex(r"[0-9a-f]{64}", fullmatch=True),
    prev_hash_val=st.from_regex(r"[0-9a-f]{64}", fullmatch=True),
)
@settings(max_examples=100)
def test_audit_log_internal_exposes_hash_fields(
    actor_role: str,
    action: str,
    resource_type: str,
    resource_id: str,
    timestamp: datetime,
    actor_user: str,
    hash_val: str,
    prev_hash_val: str,
) -> None:
    """
    **Validates: Requirements 7.3**

    Confirms the complement of Property 5: AuditLogInternal (served to officers)
    MUST expose `hash`, `prev_hash`, and `actor_user` — these fields must not
    be accidentally removed from the Internal schema.
    """
    entry = AuditLogInternal(
        id=1,
        actor_role=actor_role,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        timestamp=timestamp,
        actor_user=actor_user,
        hash=hash_val,
        prev_hash=prev_hash_val,
    )
    keys = _keys(entry)
    assert "hash" in keys, "AuditLogInternal MUST expose 'hash' for officers"
    assert "prev_hash" in keys, "AuditLogInternal MUST expose 'prev_hash' for officers"
    assert "actor_user" in keys, "AuditLogInternal MUST expose 'actor_user' for officers"


@given(
    id=_positive_int,
    ulpin=_ulpin,
    deed_no=_text,
    deed_type=st.sampled_from(["SALE", "GIFT", "MORTGAGE"]),
    registration_date=_date,
    sro_office=_text,
    buyer=_text,
    seller=_text,
    stamp_duty_paid=_bool,
    transaction_value=_positive_int,
)
@settings(max_examples=100)
def test_registration_internal_exposes_transaction_value(
    id: int,
    ulpin: str,
    deed_no: str,
    deed_type: str,
    registration_date: date,
    sro_office: str,
    buyer: str,
    seller: str,
    stamp_duty_paid: bool,
    transaction_value: int,
) -> None:
    """
    **Validates: Requirements 7.3**

    RegistrationInternal (served to officers) MUST expose `transaction_value`.
    This is the complement test: confirms Internal schemas are not over-masked.
    """
    entry = RegistrationInternal(
        id=id,
        ulpin=ulpin,
        deed_no=deed_no,
        deed_type=deed_type,
        registration_date=registration_date,
        sro_office=sro_office,
        buyer=buyer,
        seller=seller,
        stamp_duty_paid=stamp_duty_paid,
        transaction_value=transaction_value,
    )
    keys = _keys(entry)
    assert "transaction_value" in keys, (
        "RegistrationInternal MUST expose 'transaction_value' for officer callers"
    )


@given(
    ulpin=_ulpin,
    assessment_id=_text,
    payment_status=st.sampled_from(["PAID", "PENDING", "DEFAULTED"]),
    arrears=st.integers(min_value=0, max_value=1_000_000),
    annual_tax=_positive_int,
)
@settings(max_examples=100)
def test_tax_internal_exposes_annual_tax(
    ulpin: str,
    assessment_id: str,
    payment_status: str,
    arrears: int,
    annual_tax: int,
) -> None:
    """
    **Validates: Requirements 7.3**

    TaxInternal (served to TAX_OFF and above) MUST expose `annual_tax`.
    """
    entry = TaxInternal(
        ulpin=ulpin,
        assessment_id=assessment_id,
        payment_status=payment_status,
        arrears=arrears,
        annual_tax=annual_tax,
    )
    keys = _keys(entry)
    assert "annual_tax" in keys, (
        "TaxInternal MUST expose 'annual_tax' for officer callers"
    )


@given(
    ulpin=_ulpin,
    state_code=st.sampled_from(["CH", "TN", "MH"]),
    district=_text,
    tehsil=st.one_of(st.none(), _text),
    village_or_city=_text,
    area_sqm=_positive_float,
    survey_or_khasra_no=_text,
    source_system=_text,
    geom=st.one_of(st.none(), st.just('{"type":"Polygon","coordinates":[]}')),
)
@settings(max_examples=100)
def test_parcel_internal_exposes_geom(
    ulpin: str,
    state_code: str,
    district: str,
    tehsil: str | None,
    village_or_city: str,
    area_sqm: float,
    survey_or_khasra_no: str,
    source_system: str,
    geom: str | None,
) -> None:
    """
    **Validates: Requirements 7.3**

    ParcelInternal (served to officers) MUST expose `geom` (full GeoJSON polygon).
    """
    entry = ParcelInternal(
        ulpin=ulpin,
        state_code=state_code,
        district=district,
        tehsil=tehsil,
        village_or_city=village_or_city,
        area_sqm=area_sqm,
        survey_or_khasra_no=survey_or_khasra_no,
        source_system=source_system,
        geom=geom,
    )
    keys = _keys(entry)
    # geom key must be present in Internal schema (even if the value is None)
    assert "geom" in keys, (
        "ParcelInternal MUST expose 'geom' field for officer callers"
    )
