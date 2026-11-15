# Requirements Document

## Introduction

Track A implements the complete FastAPI + PostGIS backend for Land Stack (SIH PS #26014), a national land-governance platform. The backend exposes a REST API consumed by the React frontend (Track B). All functional contracts are **frozen** in the docs directory; this document references them as the authoritative source of truth and adds structured acceptance criteria for implementation.

Frozen contract documents:
- `docs/DATA_SCHEMA.md` — canonical table definitions, all fields, FK relationships via ULPIN
- `docs/RBAC_MATRIX.md` — 7 roles, field-masking rules, endpoint → role mapping
- `docs/API_SPEC.md` — full endpoint catalogue with request/response schemas and audit actions
- `docs/ARCHITECTURE.md` — system topology, event-flow diagram, State Adapter pattern

## Glossary

- **ULPIN**: Universal Land Parcel Identification Number — the single join key across all tables.
- **System**: The FastAPI backend application running on port 8000.
- **Caller**: The authenticated HTTP client making a request; identified by their JWT.
- **Role**: One of the 7 RBAC roles (CITIZEN, REV_OFF, REG_OFF, PLAN_OFF, TAX_OFF, STATE_ADMIN, NATL_ADMIN).
- **Jurisdiction**: The `state_code` bound to an officer-role JWT; CITIZEN and NATL_ADMIN have null jurisdiction (unrestricted public/national scope).
- **Envelope**: The standard JSON response wrapper `{success, data, errors}` defined in `docs/API_SPEC.md`.
- **Audit Chain**: The SHA-256 hash-chained `audit_log` table where each row's `hash` = SHA-256(`prev_hash` + row contents).
- **Public Schema**: A Pydantic response model that omits or masks sensitive fields per `docs/RBAC_MATRIX.md` — served to CITIZEN callers.
- **Internal Schema**: A Pydantic response model that includes all fields — served to officer and admin callers.
- **Workflow Engine**: The Redis pub/sub consumer (`workflow_engine/consumer.py`) that reacts to domain events and creates/progresses `workflow_tasks`.
- **State Adapter**: The `state_adapter_config` table and seed data that maps each state's native field names to canonical field names.
- **ML Module**: The three AI/ML scripts (`change_detection.py`, `fraud_score.py`, `ocr_extraction.py`) that back the `/ml/*` routes.

---

## Requirements

### Requirement 1: Application Foundation

**User Story:** As a backend developer, I want a correctly scaffolded FastAPI application with router aggregation and standard response envelope, so that every downstream feature starts from a consistent, testable baseline.

#### Acceptance Criteria

1. THE System SHALL expose a FastAPI application in `backend/main.py` that mounts all domain routers under the `/api/v1` prefix.
2. THE System SHALL wrap every JSON response in an envelope `{success: bool, data: any, errors: list}` as defined in `docs/API_SPEC.md`.
3. THE System SHALL provide a SQLAlchemy 2.0 async-compatible engine and session factory in `backend/core/database.py` connected to a PostgreSQL/PostGIS instance.
4. THE System SHALL include an Alembic configuration (`backend/alembic.ini`, `backend/alembic/env.py`) targeting the same database.

---

### Requirement 2: Database Models

**User Story:** As a backend developer, I want SQLAlchemy 2.0 ORM models for every table in `docs/DATA_SCHEMA.md`, so that all persistence logic is type-safe and GIS-capable.

#### Acceptance Criteria

1. THE System SHALL define SQLAlchemy models for the tables: `parcel`, `ror`, `registration`, `encumbrance`, `zoning`, `building_permission`, `tax`, `audit_log`, `state_adapter_config`, `workflow_tasks`, `citizen_service_requests`, `users`.
2. THE System SHALL use `GeoAlchemy2` `Geometry("POLYGON", srid=4326)` for `parcel.geom`.
3. THE System SHALL enforce FK relationships keyed on `ulpin` as documented in `docs/DATA_SCHEMA.md`.
4. THE System SHALL generate an Alembic initial migration (`versions/001_initial.py`) that creates all tables with upgrade and downgrade steps.

---

### Requirement 3: Seed Data

**User Story:** As a developer/tester, I want a seed loader that populates all tables from the `seed-data/` files, so that a fresh environment has representative data for testing.

#### Acceptance Criteria

1. THE System SHALL provide `backend/scripts/seed_loader.py` that loads all seed files: `chandigarh_parcels.geojson`, `tn_village_parcels.geojson`, `ror.json`, `registration.json`, `encumbrance.json`, `zoning.json`, `building_permission.json`, `tax.json`, `users.json`, `state_adapter_config.json`.
2. WHEN a seed record's ULPIN already exists in the database, THE System SHALL upsert (update) rather than raise a duplicate-key error.

---

### Requirement 4: Authentication

**User Story:** As a user, I want to log in and receive JWT tokens, so that I can make authenticated API calls.

#### Acceptance Criteria

1. WHEN a caller POSTs valid credentials to `/auth/login`, THE System SHALL issue an access token (15-minute expiry) and a refresh token (7-day expiry) signed with HS256.
2. WHEN a caller POSTs a valid refresh token to `/auth/refresh`, THE System SHALL issue a new access token without requiring re-login.
3. WHEN a caller POSTs to `/auth/logout`, THE System SHALL add the token pair to a Redis blacklist so they cannot be reused.
4. WHEN a request carries a blacklisted or expired token, THE System SHALL return HTTP 401 with error code `UNAUTHORIZED`.

---

### Requirement 5: RBAC and Jurisdiction

**User Story:** As a system operator, I want role-based access control enforced on every route, so that officers can only access data within their authority.

#### Acceptance Criteria

1. THE System SHALL provide a `get_current_user` FastAPI dependency that extracts and validates the JWT on every protected route.
2. THE System SHALL provide a `require_role(roles)` dependency factory used as `Depends(require_role([...]))` on every route per `docs/RBAC_MATRIX.md`.
3. WHEN a caller's role is not in the allowed set for the endpoint, THE System SHALL return HTTP 403 with error code `FORBIDDEN`.
4. THE System SHALL provide a `check_jurisdiction` dependency that verifies the parcel's `state_code` matches the officer's jurisdiction for state-scoped roles.
5. WHEN a caller's jurisdiction does not match the parcel's state_code, THE System SHALL return HTTP 403 with error code `FORBIDDEN`.

---

### Requirement 6: Audit Log

**User Story:** As a compliance officer, I want a tamper-evident, hash-chained audit log written on every write/approve action, so that I can detect unauthorized modifications.

#### Acceptance Criteria

1. WHEN any write or approve action succeeds, THE System SHALL write an `audit_log` row before returning the success response.
2. THE System SHALL compute each row's `hash` as SHA-256 of (`prev_hash` + serialized row contents) using `backend/core/audit.py`.
3. THE System SHALL store the `prev_hash` of the immediately preceding `audit_log` row in each new row, forming a verifiable chain.
4. WHEN queried by CITIZEN callers, THE System SHALL omit `actor_user`, `hash`, and `prev_hash` fields (Public schema masking per `docs/RBAC_MATRIX.md`).

---

### Requirement 7 — Pydantic Response Schemas

**User Story:** As a backend developer, I want Public and Internal Pydantic schemas for every resource, so that field-masking is enforced at the serialization layer.

#### Acceptance Criteria

1. THE System SHALL define `Public` and `Internal` Pydantic response schemas for every resource per the masking rules in `docs/RBAC_MATRIX.md`.
2. WHEN the caller's role is `CITIZEN`, THE System SHALL serialize responses using the `Public` schema.
3. WHEN the caller's role is any officer or admin role, THE System SHALL serialize responses using the `Internal` schema.
4. THE System SHALL omit `transaction_value` from `RegistrationPublic`.
5. THE System SHALL show only centroid + area (not the full polygon) in `ParcelPublic.geom`.

---

### Requirement 8 — Domain Routers

**User Story:** As a frontend engineer, I want all endpoints from `docs/API_SPEC.md` implemented, so that the UI can call them.

#### Acceptance Criteria

1. THE System SHALL implement all endpoints defined in `docs/API_SPEC.md` for the following routers: `auth`, `parcel`, `ror`, `registration`, `encumbrance`, `zoning`, `building_permission`, `tax`, `workflow`, `citizen`, `admin`, `analytics`.
2. WHEN a resource referenced by ULPIN is not found, THE System SHALL return HTTP 404 with error code `NOT_FOUND`.
3. WHEN a request body fails Pydantic validation, THE System SHALL return HTTP 422 with error code `VALIDATION_ERROR`.
4. THE System SHALL apply `Depends(require_role([...]))` on every route exactly as specified in `docs/RBAC_MATRIX.md`.

---

### Requirement 9 — Workflow Engine

**User Story:** As a Revenue Officer, I want mutation and tax-reassessment tasks created automatically after a deed is registered, so that cross-department work is coordinated without manual handoffs.

#### Acceptance Criteria

1. WHEN `registration.completed` is published to Redis, THE System SHALL create a `workflow_tasks` record of type `MUTATION` assigned to the `REV_OFF` role for the parcel's jurisdiction.
2. WHEN `mutation.approved` is published to Redis, THE System SHALL trigger a tax reassessment by updating the `tax` record for the parcel and writing an audit log entry.
3. THE System SHALL run the Workflow Engine consumer as a background task within the FastAPI process (using `asyncio` or `BackgroundTasks`).

---

### Requirement 10 — AI/ML Endpoints

**User Story:** As a Planning Officer, I want satellite change detection, fraud scoring, and OCR extraction endpoints, so that I can detect FAR violations and anomalous registrations.

#### Acceptance Criteria

1. WHEN a caller POSTs two images to `/ml/change-detection`, THE System SHALL compute changed area using OpenCV and update `zoning.far_existing` and `zoning.violation_flag`.
2. WHEN a caller POSTs a transaction to `/ml/fraud-score`, THE System SHALL score it with a pre-trained Isolation Forest and return `fraud_score` and `flagged` fields.
3. WHEN a caller POSTs a scan image to `/ml/ocr-extract`, THE System SHALL extract `owner_name`, `survey_or_khasra_no`, and `khatauni_no` using pytesseract and return a `confidence` float.
4. WHEN any ML endpoint performs a write side-effect, THE System SHALL write an audit log entry before returning.

---

### Requirement 11 — OpenAPI Export

**User Story:** As a Track B frontend developer, I want a frozen `openapi.yaml` file, so that I can generate type-safe API clients without depending on the live backend.

#### Acceptance Criteria

1. THE System SHALL export the FastAPI-generated OpenAPI schema to `backend/openapi.yaml` via a script or CLI command.
2. THE System SHALL keep `backend/openapi.yaml` in version control so Track B can reference it offline.

---

### Requirement 12 — Test Suite

**User Story:** As a CI engineer, I want a pytest suite that covers every router with an in-process TestClient, so that regressions are caught before merge.

#### Acceptance Criteria

1. THE System SHALL provide pytest test files in `backend/tests/` for every router: `test_auth.py`, `test_parcel.py`, `test_ror.py`, `test_registration.py`, `test_encumbrance.py`, `test_zoning.py`, `test_tax.py`, `test_workflow.py`, `test_citizen.py`, `test_ml.py`.
2. WHEN the test suite is run with `pytest backend/tests/`, THE System SHALL report zero failures.
3. THE System SHALL use `httpx.AsyncClient` with the FastAPI `TestClient` transport — no live network calls during tests.
