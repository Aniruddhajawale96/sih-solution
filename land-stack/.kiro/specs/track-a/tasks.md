# Implementation Plan: Land Stack Track A — FastAPI + PostGIS Backend

## Overview

Implements the complete Python/FastAPI backend for Land Stack (SIH PS #26014). All functional contracts are frozen in `docs/`; tasks reference those documents as the authoritative source. Every task targets a specific file or set of files in `backend/`. The implementation language is **Python 3.11**.

---

## Tasks

- [x] 1. Scaffold application foundation and core infrastructure
  - [x] 1.1 Create `backend/core/database.py` with SQLAlchemy 2.0 async engine
    - Define `Base = DeclarativeBase()`, `create_async_engine`, `async_sessionmaker`, and `get_db` dependency yielding `AsyncSession`
    - Read `DATABASE_URL` from environment variable; support `postgresql+asyncpg://` scheme
    - _Requirements: 1.3_

  - [x] 1.2 Create `backend/core/schemas.py` with shared Pydantic envelope
    - Define `ErrorDetail(code, message, field)`, `Envelope[T](success, data, errors)`, `ok(data)`, and `err(code, message, field)` helpers
    - All routers import and return `Envelope[...]`
    - _Requirements: 1.2_

  - [x] 1.3 Write property test for response envelope invariant
    - **Property 4: Response envelope invariant**
    - **Validates: Requirements 1.2**
    - Generate arbitrary route responses and assert all contain `success`, `data`, `errors` keys

  - [x] 1.4 Create `backend/main.py` — FastAPI app with router aggregation and lifespan
    - Instantiate `FastAPI(title="Land Stack API", version="1.0")` with `/api/v1` prefix
    - Register lifespan context: start Workflow Engine consumer, connect Redis
    - Add global exception handlers that return `Envelope` on 404/422/500
    - Mount all domain routers (stubs acceptable at this stage — wire real routers in later tasks)
    - _Requirements: 1.1_

  - [x] 1.5 Create `backend/alembic.ini` and `backend/alembic/env.py`
    - Configure Alembic to use `asyncpg` driver and import `Base.metadata`
    - Implement `run_async_migrations()` for async upgrade support
    - _Requirements: 1.4_

  - [x] 1.6 Create `backend/Dockerfile`
    - Base: `python:3.11-slim`; install `libgdal-dev`, `tesseract-ocr`, then `pip install -r requirements.txt`
    - CMD: `uvicorn main:app --host 0.0.0.0 --port 8000`
    - _Requirements: 1.1_

---

- [x] 2. Database models and initial migration
  - [x] 2.1 Implement SQLAlchemy models for Base Layer and security tables
    - `backend/models/parcel.py`: `Parcel` with `ulpin` (String PK), `state_code`, `district`, `tehsil`, `village_or_city`, `geom` (`Geometry("POLYGON", srid=4326)`), `area_sqm`, `survey_or_khasra_no`, `source_system`, `last_synced_at`
    - `backend/models/users.py`: `User` with `username` (PK), `hashed_password`, `role`, `jurisdiction`, `is_active`
    - `backend/models/audit_log.py`: `AuditLog` with int `id` PK, `actor_user`, `actor_role`, `action`, `resource_type`, `resource_id`, `timestamp`, `hash`, `prev_hash`
    - _Requirements: 2.1, 2.2, 2.3_

  - [x] 2.2 Implement SQLAlchemy models for Essential Layer
    - `backend/models/ror.py`: `Ror` — `ulpin` FK → parcel, `owner_name`, `tenure_type`, `khatauni_no`, `land_use_type`, `mutation_status`, `last_updated`
    - `backend/models/registration.py`: `Registration` — int `id` PK, `ulpin` FK, `deed_no`, `deed_type`, `registration_date`, `sro_office`, `buyer`, `seller`, `transaction_value`, `stamp_duty_paid`
    - `backend/models/encumbrance.py`: `Encumbrance` — int `id` PK, `ulpin` FK, `type`, `institution`, `status`, `date`
    - `backend/models/zoning.py`: `Zoning` — `ulpin` FK (unique), `master_plan_zone`, `permissible_use`, `far_permitted`, `far_existing`, `violation_flag`
    - `backend/models/building_permission.py`: `BuildingPermission` — int `id` PK, `ulpin` FK, `approval_no`, `approved_built_up_area`, `approval_date`, `status`, `architect_ref`
    - `backend/models/tax.py`: `Tax` — `ulpin` FK (unique), `assessment_id`, `annual_tax`, `last_paid_date`, `payment_status`, `arrears`
    - _Requirements: 2.1, 2.3_

  - [x] 2.3 Implement SQLAlchemy models for workflow and state adapter tables
    - `backend/models/workflow.py`: `WorkflowTask` — int `id` PK, `ulpin` FK, `task_type` (MUTATION/TAX/ZONING), `assigned_role`, `status`, `created_at`, `resolved_at`, `comment`; `CitizenServiceRequest` — UUID string `id` PK, `ulpin`, `citizen_username`, `service_type`, `notes`, `status`, `created_at`
    - `backend/models/state_adapter.py`: `StateAdapterConfig` — int `id` PK, `state_code`, `source_field_name`, `canonical_field_name`, `unit_conversion_factor`, `language_code`
    - _Requirements: 2.1_

  - [x] 2.4 Generate Alembic initial migration `backend/alembic/versions/001_initial.py`
    - `upgrade()`: `CREATE EXTENSION IF NOT EXISTS postgis;` then `op.create_table(...)` for all 12 tables in dependency order (parcel first, then FKs)
    - `downgrade()`: drop tables in reverse order
    - _Requirements: 2.4_

  - [x] 2.5 Write property test for model round-trip serialization
    - **Property 2: Hash chain integrity** (verify `prev_hash` linkage across consecutive audit rows)
    - **Validates: Requirements 6.2, 6.3**
    - Generate N sequential audit writes; assert chain integrity across all N rows

---

- [x] 3. Security core — JWT auth, RBAC dependencies, audit chain
  - [x] 3.1 Implement `backend/core/auth.py`
    - `create_access_token(data)` → HS256 JWT, 15-min expiry, payload includes `sub`, `role`, `jurisdiction`, `jti`
    - `create_refresh_token(data)` → HS256 JWT, 7-day expiry
    - `verify_token(token, redis_client)` → decoded payload; raises `HTTPException(401)` if expired, invalid, or blacklisted
    - `blacklist_token(jti, ttl, redis_client)` → `SET jti 1 EX ttl` in Redis
    - `is_blacklisted(jti, redis_client)` → bool
    - Use `passlib[bcrypt]` for password hashing: `hash_password`, `verify_password`
    - _Requirements: 4.1, 4.2, 4.3, 4.4_

  - [x] 3.2 Implement `backend/core/rbac.py`
    - `get_current_user(token=Depends(oauth2_scheme), redis=..., db=...)` → `UserClaims` dataclass
    - `require_role(roles: list[str])` → dependency factory; raises `HTTPException(403)` for role mismatch
    - `check_jurisdiction(ulpin: str, user=Depends(get_current_user), db=...)` → passes for NATL_ADMIN/CITIZEN; raises `HTTPException(403)` when `parcel.state_code != user.jurisdiction`
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

  - [x] 3.3 Implement `backend/core/audit.py`
    - `write_audit(db, actor_user, actor_role, action, resource_type, resource_id)` → `AuditLog`
    - Fetches last row's `hash` (or `"0"*64` for first row); computes `new_hash = sha256(prev_hash + row_content)`; `db.add` within the caller's open transaction; `await db.flush()` to get the auto-id
    - _Requirements: 6.1, 6.2, 6.3_

  - [x] 3.4 Implement `backend/routers/auth.py` — POST /auth/login, POST /auth/refresh, POST /auth/logout
    - `POST /auth/login`: verify credentials via `verify_password`; return `{access_token, refresh_token, token_type, role, jurisdiction}` wrapped in `Envelope`
    - `POST /auth/refresh`: verify refresh token; issue new access token
    - `POST /auth/logout`: blacklist both tokens' JTIs in Redis
    - _Requirements: 4.1, 4.2, 4.3_

  - [x] 3.5 Write property test for role enforcement
    - **Property 3: Role enforcement — forbidden access**
    - **Validates: Requirements 5.2, 5.3**
    - Generate random (endpoint, role) pairs where role ∉ allowed set; assert all return 403 with no DB side-effects

  - [x] 3.6 Write property test for token blacklist
    - **Property 7: Token blacklist prevents reuse**
    - **Validates: Requirements 4.3, 4.4**
    - For any token that is logged out, assert all subsequent calls with that token return 401

  - [x] 3.7 Write property test for audit chain
    - **Property 1: Audit log entry exists after every write**
    - **Validates: Requirements 6.1, 6.2**
    - For any write action, assert a corresponding audit row exists with correct `resource_id` and `action`

---

- [x] 4. Checkpoint — foundation green
  - Ensure all tests pass, ask the user if questions arise.

---

- [x] 5. Pydantic response schemas for all resources
  - [x] 5.1 Write Public and Internal schemas for Base Layer and security resources in `backend/core/schemas.py` (or per-router schema files)
    - `ParcelPublic`: omit full `geom` polygon; include centroid (computed) + `area_sqm`
    - `ParcelInternal`: all fields including full GeoJSON geometry
    - `UserInternal`: all fields except `hashed_password`
    - `AuditLogPublic`: include `actor_role`, `action`, `timestamp`; omit `actor_user`, `hash`, `prev_hash`
    - `AuditLogInternal`: all fields
    - _Requirements: 7.1, 7.3, 7.4, 7.5_

  - [x] 5.2 Write Public and Internal schemas for Essential Layer resources
    - `RorPublic`: `owner_name` partially masked (`Ramesh K***`); omit `owner_id_ref`
    - `RorInternal`: all fields
    - `RegistrationPublic`: omit `transaction_value`; partial mask on `buyer`/`seller`
    - `RegistrationInternal`: all fields
    - `EncumbrancePublic` / `EncumbranceInternal`: same (no masking — public transparency)
    - `ZoningPublic` / `ZoningInternal`: same (FAR data is public)
    - `BuildingPermissionPublic` / `BuildingPermissionInternal`: same (public)
    - `TaxPublic`: omit `annual_tax`; include `arrears`, `payment_status`
    - `TaxInternal`: all fields
    - _Requirements: 7.1, 7.2, 7.4, 7.5_

  - [x] 5.3 Write schemas for Workflow, Citizen, Admin, and ML resources
    - `WorkflowTask`, `CitizenServiceRequest`, `StateAdapterConfig`, `StateAdapterConfigUpdate`
    - ML response schemas: `ChangeDetectionResponse`, `FraudScoreResponse`, `OcrExtractResponse`
    - _Requirements: 7.1_

  - [x] 5.4 Write property test for CITIZEN field masking
    - **Property 5: Field masking — CITIZEN never receives hidden fields**
    - **Validates: Requirements 7.2, 7.4, 7.5**
    - For any resource instance, serialize with `Public` schema; assert `transaction_value`, `owner_id_ref`, `hash`, `prev_hash`, full polygon are all absent from the output

---

- [x] 6. Seed loader and data scripts
  - [x] 6.1 Implement `backend/scripts/seed_loader.py`
    - Load `state_adapter_config.json` first; build field-mapping dict keyed by `state_code`
    - Load GeoJSON parcels (`chandigarh_parcels.geojson`, `tn_village_parcels.geojson`) using `shapely`/GeoAlchemy2 `ST_GeomFromGeoJSON`; upsert on `ulpin` via `on_conflict_do_update`
    - Load remaining JSON seed files (`ror.json`, `registration.json`, `encumbrance.json`, `zoning.json`, `building_permission.json`, `tax.json`, `users.json`) in FK dependency order; apply State Adapter unit conversions (multiply numeric fields by `unit_conversion_factor`)
    - Hash passwords in `users.json` with `passlib` before insert
    - _Requirements: 3.1, 3.2_

---

- [x] 7. Domain routers — Base Layer and Record of Rights
  - [x] 7.1 Implement `backend/routers/parcel.py`
    - `GET /parcels/{ulpin}`: fetch parcel; return `ParcelPublic` for CITIZEN, `ParcelInternal` for officers; require `Depends(require_role([all roles]))` + `Depends(check_jurisdiction)` for officer roles
    - `GET /parcels/search`: filter by `q`, `state_code`, `district`, `bbox` (PostGIS `ST_Intersects`); paginate with `limit`/`offset`; return list of `ParcelPublic`/`ParcelInternal`
    - `POST /parcels`: require `REV_OFF, STATE_ADMIN, NATL_ADMIN`; create parcel; write audit `CREATE_PARCEL`; return 201 `ParcelInternal`
    - _Requirements: 8.1, 8.2, 8.3, 8.4_

  - [x] 7.2 Implement `backend/routers/ror.py`
    - `GET /ror/{ulpin}`: return `RorPublic` for CITIZEN, `RorInternal` for officers
    - `PUT /ror/{ulpin}`: require `REV_OFF, STATE_ADMIN, NATL_ADMIN`; update fields; write audit `UPDATE_ROR`; publish `ror.mutation_status_changed` event when `mutation_status` flips; return `RorInternal`
    - _Requirements: 8.1, 8.4_

  - [x] 7.3 Write tests for parcel and ror routers (`backend/tests/test_parcel.py`, `backend/tests/test_ror.py`)
    - Test GET by valid ULPIN returns 200; GET with unknown ULPIN returns 404
    - Test CITIZEN gets `ParcelPublic` (no polygon); officer gets `ParcelInternal`
    - Test POST parcel by REV_OFF creates row and audit entry; POST by CITIZEN returns 403
    - Test PUT /ror by REV_OFF updates row and writes audit; test jurisdiction mismatch returns 403
    - _Requirements: 12.1, 12.2_

---

- [x] 8. Domain routers — Registration, Encumbrance, Zoning, Building Permission, Tax
  - [x] 8.1 Implement `backend/routers/registration.py`
    - `POST /registration`: require `REG_OFF, STATE_ADMIN, NATL_ADMIN`; insert `Registration`; write audit `REGISTER_DEED`; publish `registration.completed` to Redis; return 201 `RegistrationInternal`
    - `GET /registration`: filterable list; return `RegistrationPublic` for CITIZEN/REV_OFF (omit `transaction_value`)
    - `GET /registration/{id}`: single record with masking
    - _Requirements: 8.1, 8.4_

  - [x] 8.2 Implement `backend/routers/encumbrance.py`
    - `POST /encumbrance`: require `REG_OFF, STATE_ADMIN, NATL_ADMIN`; write audit `CREATE_ENCUMBRANCE`; return 201 `EncumbranceInternal`
    - `GET /encumbrance/{ulpin}`: public, no masking; return list
    - _Requirements: 8.1, 8.4_

  - [x] 8.3 Implement `backend/routers/zoning.py`
    - `PUT /zoning/{ulpin}`: require `PLAN_OFF, STATE_ADMIN, NATL_ADMIN`; write audit `UPDATE_ZONING`; return `ZoningInternal`
    - `GET /zoning/{ulpin}`: public; return `ZoningPublic`
    - _Requirements: 8.1, 8.4_

  - [x] 8.4 Implement `backend/routers/building_permission.py`
    - `POST /building-permission`: require `PLAN_OFF, STATE_ADMIN, NATL_ADMIN`; write audit `CREATE_BUILDING_PERMISSION`; return 201 `BuildingPermissionInternal`
    - `GET /building-permission/{ulpin}`: public; return list
    - _Requirements: 8.1, 8.4_

  - [x] 8.5 Implement `backend/routers/tax.py`
    - `GET /tax/{ulpin}`: return `TaxPublic` for CITIZEN (omit `annual_tax`)
    - `PUT /tax/{ulpin}`: require `TAX_OFF, STATE_ADMIN, NATL_ADMIN`; write audit `REASSESS_TAX`; return `TaxInternal`
    - _Requirements: 8.1, 8.4_

  - [x] 8.6 Write tests for registration, encumbrance, zoning, building_permission, tax routers
    - `backend/tests/test_registration.py`: POST by REG_OFF → 201 + audit row + Redis publish; GET by CITIZEN omits `transaction_value`; jurisdiction mismatch → 403
    - `backend/tests/test_encumbrance.py`: POST then GET; `institution` present in public response
    - `backend/tests/test_zoning.py`: PUT then GET; `violation_flag` reflects `far_existing > far_permitted`
    - `backend/tests/test_tax.py`: GET by CITIZEN omits `annual_tax`; PUT by TAX_OFF writes audit
    - _Requirements: 12.1, 12.2_

---

- [x] 9. Checkpoint — domain routers green
  - Ensure all tests pass, ask the user if questions arise.

---

- [x] 10. Workflow Engine and Workflow router
  - [x] 10.1 Implement `backend/workflow_engine/consumer.py`
    - Async Redis subscriber using `redis.asyncio`; subscribe to `registration.completed` and `mutation.approved`
    - `registration.completed` handler: open DB session, `db.add(WorkflowTask(task_type="MUTATION", assigned_role="REV_OFF", status="pending", ulpin=...))`, commit
    - `mutation.approved` handler: load `Tax` row for `ulpin`; call tax-reassessment logic (recalculate `annual_tax` if needed); write audit `REASSESS_TAX`; commit
    - Start consumer as `asyncio.create_task` inside FastAPI lifespan
    - _Requirements: 9.1, 9.2, 9.3_

  - [x] 10.2 Implement `backend/routers/workflow.py`
    - `GET /workflow/tasks`: scope to caller's `role` + `jurisdiction`; filterable by `status`, `assigned_role`
    - `POST /workflow/{taskId}/approve`: validate task-type → role match; set `status="approved"`, `resolved_at`, `comment`; write audit; publish `mutation.approved` or `zoning.approved` etc. to Redis; return `{task_id, status, next_event}`
    - `POST /workflow/{taskId}/reject`: set `status="rejected"`; write audit `REJECT_MUTATION`
    - `GET /workflow/events/stream`: SSE endpoint reading from Redis `SUBSCRIBE`; each message emitted as `data: {JSON}\n\n`
    - _Requirements: 8.1, 9.1, 9.2_

  - [x] 10.3 Write property test for workflow event chain
    - **Property 8: Workflow event chain**
    - **Validates: Requirements 9.1**
    - For any `registration.completed` event, assert exactly one `workflow_tasks` row of type `MUTATION` is created with matching `ulpin`

  - [x] 10.4 Write tests for workflow router (`backend/tests/test_workflow.py`)
    - Test approve by correct role → audit + next event; reject by correct role → audit
    - Test approve by wrong role type → 403 (e.g. TAX_OFF cannot approve a MUTATION task)
    - Test SSE stream returns valid event-stream content-type
    - _Requirements: 12.1, 12.2_

---

- [x] 11. Citizen Services router
  - [x] 11.1 Implement `backend/routers/citizen.py`
    - `POST /citizen/service-request`: require `CITIZEN`; insert `CitizenServiceRequest`; write audit `CITIZEN_SERVICE_REQUEST`; return 201 `{request_id, status}`
    - `GET /citizen/requests`: require `CITIZEN`; return requests scoped to `current_user.username`
    - `GET /citizen/parcels`: require `CITIZEN`; query `ror.owner_name` ILIKE `%citizen_name%` to find owned parcels; return list of `ParcelPublic`
    - _Requirements: 8.1, 8.4_

  - [x] 11.2 Write tests for citizen router (`backend/tests/test_citizen.py`)
    - Test service request submission returns 201 with `request_id`
    - Test GET /citizen/requests scoped to current user (cannot see other users' requests)
    - Test officer calling `/citizen/service-request` returns 403
    - _Requirements: 12.1, 12.2_

---

- [x] 12. Admin and Analytics routers
  - [x] 12.1 Implement `backend/routers/admin.py`
    - `GET /admin/state-adapter/{state_code}`: require `STATE_ADMIN` (own state) or `NATL_ADMIN`; return config list
    - `PUT /admin/state-adapter/{state_code}`: require `NATL_ADMIN`; update config; write audit `UPDATE_STATE_ADAPTER`
    - `GET /admin/users`: require `STATE_ADMIN` (own jurisdiction) or `NATL_ADMIN`; return `UserInternal` list (no `hashed_password`)
    - _Requirements: 8.1, 8.4_

  - [x] 12.2 Implement `backend/routers/analytics.py`
    - `GET /analytics/national`: require `NATL_ADMIN`; run aggregate SQL: total parcels, group by state_code, count violations, pending mutations, fraud flags
    - `GET /analytics/state/{state_code}`: require `STATE_ADMIN` (own) or `NATL_ADMIN`; state-scoped aggregates
    - `GET /analytics/audit/{ulpin}`: all roles; return `AuditLogPublic` list for CITIZEN, `AuditLogInternal` for officers; ordered by `id` ascending (chain order)
    - _Requirements: 8.1, 8.4_

---

- [x] 13. AI/ML modules and routes
  - [x] 13.1 Implement `backend/ml/change_detection.py`
    - Accept two image byte arrays; use OpenCV (`cv2.absdiff`, threshold, contour area) to compute `changed_area_sqm`
    - Estimate `far_existing_est` from changed area and parcel `area_sqm`; set `violation_flag = far_existing_est > far_permitted`
    - Return `ChangeDetectionResult` dataclass
    - _Requirements: 10.1_

  - [x] 13.2 Implement `backend/ml/fraud_score.py`
    - Load pre-trained `IsolationForest` from pickle file (or train on seed registration data at startup if file absent)
    - Feature vector: `[transaction_value, log(transaction_value), area_sqm, value_per_sqm]`
    - `score_transaction(ulpin, deed_no, transaction_value, parcel_area_sqm)` → `{fraud_score: float, flagged: bool}` where `flagged = fraud_score < -0.1`
    - _Requirements: 10.2_

  - [x] 13.3 Implement `backend/ml/ocr_extraction.py`
    - `extract_ror_fields(image_bytes, state_code)` → preprocess with OpenCV (denoise, threshold); run `pytesseract.image_to_string`; apply regex patterns for `owner_name`, `survey_or_khasra_no`, `khatauni_no`; compute `confidence` from pytesseract confidence scores
    - _Requirements: 10.3_

  - [x] 13.4 Implement `backend/routers/ml.py` — POST /ml/change-detection, /ml/fraud-score, /ml/ocr-extract
    - `POST /ml/change-detection`: require `PLAN_OFF, STATE_ADMIN, NATL_ADMIN`; call `change_detection.py`; update `zoning.far_existing` + `violation_flag`; write audit `ML_CHANGE_DETECTION`; return `ChangeDetectionResponse`
    - `POST /ml/fraud-score`: require `REG_OFF, STATE_ADMIN, NATL_ADMIN`; call `fraud_score.py`; write audit `ML_FRAUD_SCORE`; return `FraudScoreResponse`
    - `POST /ml/ocr-extract`: require `REV_OFF, STATE_ADMIN, NATL_ADMIN`; call `ocr_extraction.py`; write audit `ML_OCR_EXTRACT`; return `OcrExtractResponse`
    - _Requirements: 10.1, 10.2, 10.3, 10.4_

  - [x] 13.5 Write tests for ML routes (`backend/tests/test_ml.py`)
    - Mock OpenCV/pytesseract/sklearn calls; test each ML route returns correct schema shape
    - Test audit rows are written for each ML action
    - Test wrong role returns 403 on each ML route (CITIZEN, wrong officer type)
    - _Requirements: 12.1, 12.2_

---

- [x] 14. Checkpoint — full backend green
  - Ensure all tests pass, ask the user if questions arise.

---

- [x] 15. Auth test suite and jurisdiction property tests
  - [x] 15.1 Write `backend/tests/test_auth.py`
    - Test valid login returns 200 wiscm-history-item:d%3A%5Csih-solution?%7B%22repositoryId%22%3A%22scm0_0%22%2C%22historyItemId%22%3A%2249762869533804a4ab9dd4e8a702b4b472441380%22%2C%22historyItemParentId%22%3A%224470c496e720843983052c1e40a2dc4b0db93941%22%2C%22historyItemDisplayId%22%3A%224976286%22%7Dth both tokens
    - Test refresh with valid refresh token returns new access token
    - Test logout blacklists token: subsequent request with same token returns 401
    - Test expired token returns 401
    - _Requirements: 12.1, 12.2_

  - [x] 15.2 Write property test for jurisdiction scoping
    - **Property 6: Jurisdiction scoping**
    - **Validates: Requirements 5.4, 5.5**
    - Generate officer JWTs with random `jurisdiction` values; for any parcel whose `state_code != jurisdiction`, assert 403 on write endpoints

---

- [x] 16. OpenAPI export
  - [x] 16.1 Export `backend/openapi.yaml` from live FastAPI app
    - Run `python -c "import yaml, json; from main import app; print(yaml.dump(app.openapi()))" > backend/openapi.yaml` (or equivalent script)
    - Commit `openapi.yaml` to version control so Track B can generate TypeScript types offline
    - _Requirements: 11.1, 11.2_

---

- [x] 17. Final checkpoint — all tests pass, OpenAPI committed
  - Ensure all tests pass with `pytest backend/tests/ -v`; ensure `backend/openapi.yaml` is committed and readable.
  - Ensure all tests pass, ask the user if questions arise.

---

## Notes

- Tasks marked with `*` are optional and can be skipped for a faster MVP, but each maps to a specific Correctness Property from `design.md`.
- **ULPIN is the join key in every query.** Every model FK and every route param must use it.
- **Audit before commit**: `write_audit(...)` must be called inside the same DB transaction as the mutation, before `db.commit()`. Use `db.flush()` after `write_audit` to get the row id without committing.
- **Envelope on every response**: every `return` in a router handler must pass through `ok(...)` or `err(...)`.
- **RBAC on every route**: use `Depends(require_role([...]))` with the exact role list from `docs/RBAC_MATRIX.md` — the matrix is the authoritative source, not the API spec prose.
- Tests use `httpx.AsyncClient` with FastAPI's ASGI transport — no live PostgreSQL or Redis during unit tests; use dependency overrides for `get_db` and Redis client.
- Property test tasks each map to a named Correctness Property in `design.md`; annotate with property number when implementing.

---

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2"] },
    { "id": 1, "tasks": ["1.3", "1.4", "1.5", "1.6", "2.1", "2.2", "2.3"] },
    { "id": 2, "tasks": ["2.4", "5.1", "5.2", "5.3"] },
    { "id": 3, "tasks": ["2.5", "3.1", "3.2", "3.3", "5.4", "6.1"] },
    { "id": 4, "tasks": ["3.4", "3.5", "3.6", "3.7"] },
    { "id": 5, "tasks": ["7.1", "7.2", "8.1", "8.2", "8.3", "8.4", "8.5"] },
    { "id": 6, "tasks": ["7.3", "8.6", "10.1", "11.1", "12.1", "12.2"] },
    { "id": 7, "tasks": ["10.2", "10.3", "10.4", "11.2", "13.1", "13.2", "13.3"] },
    { "id": 8, "tasks": ["13.4", "15.1", "15.2"] },
    { "id": 9, "tasks": ["13.5", "16.1"] }
  ]
}
```
