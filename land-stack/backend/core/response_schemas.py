"""
core/response_schemas.py — Public and Internal Pydantic response schemas for every resource.

Masking rules are enforced by selecting the correct schema class at the router level:
  - CITIZEN callers → Public schema (fields omitted or masked per RBAC_MATRIX.md)
  - Officer / Admin callers → Internal schema (all fields)

All schemas use Pydantic v2 with `ConfigDict(from_attributes=True)` (replaces
the v1 `class Config: orm_mode = True` pattern).

Do NOT put Envelope, ErrorDetail, ok(), or err() here — those live in core/schemas.py.
"""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


# ---------------------------------------------------------------------------
# Masking helpers
# ---------------------------------------------------------------------------


def mask_owner_name(name: str) -> str:
    """Partially mask a full name for public display.

    Examples:
        'Ramesh Kumar'   -> 'Ramesh K***'
        'Priya'          -> 'P***'
        'Vikram Singh Rawat' -> 'Vikram S***'  (only first two parts considered)
    """
    parts = name.strip().split()
    if len(parts) == 1:
        return parts[0][0] + "***"
    return parts[0] + " " + parts[1][0] + "***"


def mask_name(name: str) -> str:
    """Alias for mask_owner_name — applied to buyer/seller names on Registration."""
    return mask_owner_name(name)


# ---------------------------------------------------------------------------
# Parcel schemas
# ---------------------------------------------------------------------------


class ParcelPublic(BaseModel):
    """Citizen-visible parcel data: no full polygon geometry."""

    ulpin: str
    state_code: str
    district: str
    village_or_city: str
    area_sqm: float
    survey_or_khasra_no: str
    # geom is intentionally absent — citizens only receive centroid area, not the
    # full polygon. The centroid lat/lng is computed and returned separately by the
    # router when needed (see docs/RBAC_MATRIX.md field-masking rules).

    model_config = ConfigDict(from_attributes=True)


class ParcelInternal(ParcelPublic):
    """Full parcel data for officer/admin callers — includes geometry and sync info."""

    tehsil: str | None = None
    source_system: str
    last_synced_at: datetime | None = None
    # Serialised as a GeoJSON string; GeoAlchemy2 WKBElement is converted to GeoJSON
    # by the router before passing to this schema.
    geom: str | None = None


# ---------------------------------------------------------------------------
# User schemas
# ---------------------------------------------------------------------------


class UserInternal(BaseModel):
    """User record returned by admin endpoints — hashed_password is NEVER included."""

    username: str
    role: str
    jurisdiction: str | None = None
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# AuditLog schemas
# ---------------------------------------------------------------------------


class AuditLogPublic(BaseModel):
    """Citizen-visible audit entry — actor_user, hash, prev_hash are omitted."""

    actor_role: str
    action: str
    resource_type: str
    resource_id: str
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)


class AuditLogInternal(AuditLogPublic):
    """Full audit entry for officer/admin callers — includes identity and chain fields."""

    id: int
    actor_user: str
    hash: str
    prev_hash: str


# ---------------------------------------------------------------------------
# RoR (Record of Rights) schemas
# ---------------------------------------------------------------------------


class RorPublic(BaseModel):
    """
    Citizen-visible RoR record.

    owner_name is stored unmasked in the DB; routers must call mask_owner_name()
    before constructing this schema (or use a validator at serialisation time).
    """

    ulpin: str
    owner_name: str  # masked at call site with mask_owner_name()
    tenure_type: str
    khatauni_no: str
    land_use_type: str
    mutation_status: str
    last_updated: date

    model_config = ConfigDict(from_attributes=True)


class RorInternal(RorPublic):
    """Full RoR record for officer/admin callers — no additional masking."""

    # Inherits all fields from RorPublic; owner_name is unmasked here.
    pass


# ---------------------------------------------------------------------------
# Registration schemas
# ---------------------------------------------------------------------------


class RegistrationPublic(BaseModel):
    """
    Citizen-visible registration record — transaction_value is omitted.

    buyer and seller names should be masked with mask_name() before constructing
    this schema.
    """

    id: int
    ulpin: str
    deed_no: str
    deed_type: str
    registration_date: date
    sro_office: str
    buyer: str    # masked at call site with mask_name()
    seller: str   # masked at call site with mask_name()
    stamp_duty_paid: bool
    # transaction_value intentionally absent — hidden from public per RBAC_MATRIX.md

    model_config = ConfigDict(from_attributes=True)


class RegistrationInternal(RegistrationPublic):
    """Full registration record for REG_OFF/STATE_ADMIN/NATL_ADMIN callers."""

    transaction_value: int


# ---------------------------------------------------------------------------
# Encumbrance schemas  (no masking — public transparency requirement)
# ---------------------------------------------------------------------------


class EncumbrancePublic(BaseModel):
    """
    Encumbrance record — fully public per transparency rules.

    institution and status are always shown publicly so prospective
    buyers/lenders can verify encumbrance status.
    """

    id: int
    ulpin: str
    type: str
    institution: str
    status: str
    date: date

    model_config = ConfigDict(from_attributes=True)


# No field-level differences between public and internal views.
EncumbranceInternal = EncumbrancePublic


# ---------------------------------------------------------------------------
# Zoning schemas  (no masking — FAR data is public)
# ---------------------------------------------------------------------------


class ZoningPublic(BaseModel):
    """
    Zoning/master-plan record — fully public.

    FAR data (floor area ratio) and violation flags are intentionally
    public so citizens can verify compliance.
    """

    ulpin: str
    master_plan_zone: str
    permissible_use: str
    far_permitted: float
    far_existing: float
    violation_flag: bool

    model_config = ConfigDict(from_attributes=True)


# No field-level differences between public and internal views.
ZoningInternal = ZoningPublic


# ---------------------------------------------------------------------------
# BuildingPermission schemas  (no masking — public)
# ---------------------------------------------------------------------------


class BuildingPermissionPublic(BaseModel):
    """Building permission record — fully public."""

    id: int
    ulpin: str
    approval_no: str
    approved_built_up_area: float
    approval_date: date
    status: str
    architect_ref: str | None = None

    model_config = ConfigDict(from_attributes=True)


# No field-level differences between public and internal views.
BuildingPermissionInternal = BuildingPermissionPublic


# ---------------------------------------------------------------------------
# Tax schemas
# ---------------------------------------------------------------------------


class TaxPublic(BaseModel):
    """
    Citizen-visible tax record — annual_tax is omitted.

    arrears and payment_status are always shown publicly (public interest
    in flagging defaulters per DATA_SCHEMA.md and RBAC_MATRIX.md).
    """

    ulpin: str
    assessment_id: str
    payment_status: str
    arrears: int
    last_paid_date: date | None = None
    # annual_tax intentionally absent — hidden from public per RBAC_MATRIX.md

    model_config = ConfigDict(from_attributes=True)


class TaxInternal(TaxPublic):
    """Full tax record for TAX_OFF/STATE_ADMIN/NATL_ADMIN callers."""

    annual_tax: int


# ---------------------------------------------------------------------------
# Workflow schemas
# ---------------------------------------------------------------------------


class WorkflowTask(BaseModel):
    """Workflow task — visible to officers and admins only (not CITIZEN)."""

    id: int
    ulpin: str
    task_type: str       # MUTATION / TAX / ZONING
    assigned_role: str
    status: str          # pending / approved / rejected
    created_at: datetime
    resolved_at: datetime | None = None
    comment: str | None = None

    model_config = ConfigDict(from_attributes=True)


class CitizenServiceRequestResponse(BaseModel):
    """Citizen service request — citizen sees own requests; officers see all."""

    id: str              # UUID string PK
    ulpin: str
    citizen_username: str
    service_type: str
    notes: str | None = None
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# StateAdapterConfig schemas
# ---------------------------------------------------------------------------


class StateAdapterConfig(BaseModel):
    """State adapter mapping record."""

    id: int
    state_code: str
    source_field_name: str
    canonical_field_name: str
    unit_conversion_factor: float
    language_code: str

    model_config = ConfigDict(from_attributes=True)


class StateAdapterConfigUpdate(BaseModel):
    """Request body for NATL_ADMIN updating a state adapter mapping."""

    source_field_name: str | None = None
    canonical_field_name: str | None = None
    unit_conversion_factor: float | None = None
    language_code: str | None = None


# ---------------------------------------------------------------------------
# ML response schemas
# ---------------------------------------------------------------------------


class ChangeDetectionResponse(BaseModel):
    """Response from POST /ml/change-detection."""

    ulpin: str
    changed_area_sqm: float
    far_existing_est: float
    violation_flag: bool


class FraudScoreResponse(BaseModel):
    """Response from POST /ml/fraud-score."""

    ulpin: str
    deed_no: str
    fraud_score: float
    flagged: bool


class OcrExtractResponse(BaseModel):
    """
    Response from POST /ml/ocr-extract.

    extracted keys may include: owner_name, survey_or_khasra_no, khatauni_no.
    confidence is the mean pytesseract word-confidence (0.0–1.0).
    """

    extracted: dict[str, str]
    confidence: float


# ---------------------------------------------------------------------------
# Create / Update request body schemas
# ---------------------------------------------------------------------------


class ParcelCreate(BaseModel):
    """Request body for POST /parcels (REV_OFF, STATE_ADMIN, NATL_ADMIN)."""

    ulpin: str
    state_code: str
    district: str
    tehsil: str | None = None
    village_or_city: str
    area_sqm: float
    survey_or_khasra_no: str
    source_system: str
    # geom is provided as a GeoJSON string; the router converts it via ST_GeomFromGeoJSON
    geom: str


class RorUpdate(BaseModel):
    """Request body for PUT /ror/{ulpin} (REV_OFF, STATE_ADMIN, NATL_ADMIN)."""

    owner_name: str | None = None
    tenure_type: str | None = None
    khatauni_no: str | None = None
    land_use_type: str | None = None
    mutation_status: str | None = None


class RegistrationCreate(BaseModel):
    """Request body for POST /registration (REG_OFF, STATE_ADMIN, NATL_ADMIN)."""

    ulpin: str
    deed_no: str
    deed_type: str
    registration_date: date
    sro_office: str
    buyer: str
    seller: str
    transaction_value: int
    stamp_duty_paid: bool = False


class EncumbranceCreate(BaseModel):
    """Request body for POST /encumbrance (REG_OFF, STATE_ADMIN, NATL_ADMIN)."""

    ulpin: str
    type: str
    institution: str
    status: str
    date: date


class ZoningUpdate(BaseModel):
    """Request body for PUT /zoning/{ulpin} (PLAN_OFF, STATE_ADMIN, NATL_ADMIN)."""

    master_plan_zone: str | None = None
    permissible_use: str | None = None
    far_permitted: float | None = None


class BuildingPermissionCreate(BaseModel):
    """Request body for POST /building-permission (PLAN_OFF, STATE_ADMIN, NATL_ADMIN)."""

    ulpin: str
    approval_no: str
    approved_built_up_area: float
    approval_date: date
    status: str
    architect_ref: str | None = None


class TaxUpdate(BaseModel):
    """Request body for PUT /tax/{ulpin} (TAX_OFF, STATE_ADMIN, NATL_ADMIN)."""

    annual_tax: int | None = None
    payment_status: str | None = None
    arrears: int | None = None


# ---------------------------------------------------------------------------
# Workflow action request/response schemas  (task 5.3)
# ---------------------------------------------------------------------------


class WorkflowApproveRequest(BaseModel):
    """Request body for POST /workflow/{taskId}/approve."""

    comment: str


class WorkflowRejectRequest(BaseModel):
    """Request body for POST /workflow/{taskId}/reject."""

    reason: str


class WorkflowActionResponse(BaseModel):
    """Response from approve or reject workflow actions."""

    task_id: int
    status: str
    next_event: str | None = None


# ---------------------------------------------------------------------------
# Citizen service request schemas  (task 5.3)
# ---------------------------------------------------------------------------


class CitizenServiceRequestCreate(BaseModel):
    """Request body for POST /citizen/service-request (CITIZEN only)."""

    ulpin: str
    service_type: str    # OWNERSHIP_CERT | MUTATION_REQ | ENCUMBRANCE_CERT
    notes: str | None = None


class CitizenServiceRequestSubmitted(BaseModel):
    """Minimal confirmation returned immediately after submission."""

    request_id: str
    status: str


# ---------------------------------------------------------------------------
# Analytics schemas  (task 5.3)
# ---------------------------------------------------------------------------


class NationalAnalytics(BaseModel):
    """Aggregate stats returned by GET /analytics/national (NATL_ADMIN only)."""

    parcels_total: int
    by_state: dict[str, int]
    violations: int
    pending_mutations: int
    fraud_flags: int


class StateAnalytics(BaseModel):
    """Aggregate stats returned by GET /analytics/state/{state_code}."""

    parcels_total: int
    violations: int
    pending_mutations: int
    arrears_total: int


# ---------------------------------------------------------------------------
# Auth schemas  (task 5.3)
# ---------------------------------------------------------------------------


class LoginRequest(BaseModel):
    """Request body for POST /auth/login."""

    username: str
    password: str


class LoginResponse(BaseModel):
    """Successful login — returns both JWT tokens plus caller's role metadata."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    role: str
    jurisdiction: str | None


class RefreshRequest(BaseModel):
    """Request body for POST /auth/refresh."""

    refresh_token: str


class RefreshResponse(BaseModel):
    """New access token issued on a valid refresh."""

    access_token: str
    token_type: str = "bearer"
