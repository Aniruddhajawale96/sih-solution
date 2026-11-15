# API Specification — Land Stack

Base URL: `/api/v1`. All requests/responses are JSON unless noted. Every response is wrapped in the standard envelope (see bottom of this file). All endpoints require a valid JWT except `POST /auth/login`. RBAC and jurisdiction checks are enforced server-side on every route per docs/RBAC_MATRIX.md. Every write/approve action writes an `audit_log` entry before returning success.

Field-level masking is applied via two Pydantic response schemas per resource: a `Public` schema (CITIZEN-facing, masked) and an `Internal` schema (officer-facing, full). The backend selects which to serialize based on the caller's role.

---

## Auth

### POST /auth/login
Authenticate a user and issue access + refresh JWTs.

- **Roles**: Public (no auth required)
- **Request body**:
  ```json
  { "username": "string", "password": "string" }
  ```
- **Response 200**:
  ```json
  { "access_token": "string", "refresh_token": "string", "token_type": "bearer", "role": "CITIZEN", "jurisdiction": null }
  ```

### POST /auth/refresh
Exchange a valid refresh token for a new access token.

- **Roles**: Any authenticated user
- **Request body**:
  ```json
  { "refresh_token": "string" }
  ```
- **Response 200**:
  ```json
  { "access_token": "string", "token_type": "bearer" }
  ```

### POST /auth/logout
Invalidate the current access/refresh token pair (server-side blacklist in Redis).

- **Roles**: Any authenticated user
- **Response 200**: `{ "detail": "logged out" }`

---

## Parcel (Base Layer)

### GET /parcels/{ulpin}
Retrieve a single parcel by ULPIN, including its geometry (as GeoJSON).

- **Roles**: CITIZEN, REV_OFF, REG_OFF, PLAN_OFF, TAX_OFF, STATE_ADMIN, NATL_ADMIN
- **Path param**: `ulpin` (string)
- **Response**: `ParcelPublic` or `ParcelInternal` depending on role. CITIZEN receives masked geometry bounds only (centroid + area, not full polygon) unless authenticated as owner-verifying citizen.

### GET /parcels/search
Search parcels by spatial or attribute filters. Returns a list of parcels.

- **Roles**: All roles
- **Query params**:
  - `q` (string) — free-text match on survey_or_khasra_no, village_or_city, ulpin
  - `state_code` (string)
  - `district` (string)
  - `bbox` (string, `minx,miny,maxx,maxy`) — WGS84 bounding box for spatial search
  - `limit` (int, default 50), `offset` (int, default 0)
- **Response**: `{ "items": [ParcelPublic...], "total": int }`

### POST /parcels
Create a new parcel (Base layer). Officer-only.

- **Roles**: REV_OFF, STATE_ADMIN, NATL_ADMIN
- **Request body**: `ParcelCreate` (ulpin, state_code, district, tehsil, village_or_city, geom, area_sqm, survey_or_khasra_no, source_system)
- **Response 201**: `ParcelInternal`
- **Audit**: `action="CREATE_PARCEL"`

---

## Record of Rights (Essential Layer)

### GET /ror/{ulpin}
Retrieve the Record of Rights for a parcel.

- **Roles**: All roles. CITIZEN receives `RorPublic` (owner_name partially masked).
- **Response**: `RorPublic` / `RorInternal`

### PUT /ror/{ulpin}
Update the RoR record. Triggers audit + (if mutation_status changes) a workflow event.

- **Roles**: REV_OFF, STATE_ADMIN, NATL_ADMIN
- **Request body**: `RorUpdate` (owner_name, tenure_type, khatauni_no, land_use_type, mutation_status)
- **Response 200**: `RorInternal`
- **Audit**: `action="UPDATE_ROR"`
- **Event**: publishes `ror.mutation_status_changed` when `mutation_status` flips.

---

## Registration (Essential Layer)

### POST /registration
Register a new deed (sale/gift/lease). This is the trigger for the cross-department automated workflow.

- **Roles**: REG_OFF, STATE_ADMIN, NATL_ADMIN
- **Request body**: `RegistrationCreate` (ulpin, deed_no, deed_type, registration_date, sro_office, buyer, seller, transaction_value, stamp_duty_paid)
- **Response 201**: `RegistrationInternal`
- **Audit**: `action="REGISTER_DEED"`
- **Event**: publishes `registration.completed` -> Workflow Engine creates a mutation task.

### GET /registration
List registrations, filterable.

- **Roles**: All roles. CITIZEN/REV_OFF receive `RegistrationPublic` (transaction_value hidden).
- **Query params**: `ulpin`, `deed_type`, `sro_office`, `from_date`, `to_date`
- **Response**: `{ "items": [RegistrationPublic...], "total": int }`

### GET /registration/{id}
Retrieve a single registration record by its integer id.

- **Roles**: All roles (masking applies for public roles).
- **Response**: `RegistrationPublic` / `RegistrationInternal`

---

## Encumbrance (Essential Layer)

### POST /encumbrance
Record an encumbrance (mortgage / lien / court case).

- **Roles**: REG_OFF, STATE_ADMIN, NATL_ADMIN
- **Request body**: `EncumbranceCreate` (ulpin, type, institution, status, date)
- **Response 201**: `EncumbranceInternal`
- **Audit**: `action="CREATE_ENCUMBRANCE"`
- **Note**: `institution` is always shown publicly (transparency requirement).

### GET /encumbrance/{ulpin}
List all encumbrances for a parcel.

- **Roles**: All roles. Encumbrance data is public (no masking).
- **Response**: `{ "items": [EncumbrancePublic...] }`

---

## Zoning / Master Plan (Essential Layer)

### PUT /zoning/{ulpin}
Update zoning (master plan zone, permissible use, FAR).

- **Roles**: PLAN_OFF, STATE_ADMIN, NATL_ADMIN
- **Request body**: `ZoningUpdate` (master_plan_zone, permissible_use, far_permitted)
- **Response 200**: `ZoningInternal`
- **Audit**: `action="UPDATE_ZONING"`

### GET /zoning/{ulpin}
Retrieve zoning + FAR violation status for a parcel.

- **Roles**: All roles. `violation_flag` and FAR values are public.
- **Response**: `ZoningPublic`

---

## Building Permission (Essential Layer)

### POST /building-permission
Create a building permission record.

- **Roles**: PLAN_OFF, STATE_ADMIN, NATL_ADMIN
- **Request body**: `BuildingPermissionCreate`
- **Response 201**: `BuildingPermissionInternal`
- **Audit**: `action="CREATE_BUILDING_PERMISSION"`

### GET /building-permission/{ulpin}
List building permissions for a parcel.

- **Roles**: All roles.
- **Response**: `{ "items": [BuildingPermissionPublic...] }`

---

## Tax (Essential Layer)

### GET /tax/{ulpin}
Retrieve tax assessment for a parcel. Arrears and payment_status are public.

- **Roles**: All roles.
- **Response**: `TaxPublic`

### PUT /tax/{ulpin}
Reassess tax (typically auto-triggered after mutation approval, but exposed for manual override).

- **Roles**: TAX_OFF, STATE_ADMIN, NATL_ADMIN
- **Request body**: `TaxUpdate` (annual_tax, payment_status, arrears)
- **Response 200**: `TaxInternal`
- **Audit**: `action="REASSESS_TAX"`

---

## Workflow

### GET /workflow/tasks
List pending workflow tasks for the current officer (scoped to role + jurisdiction).

- **Roles**: REV_OFF, REG_OFF, PLAN_OFF, TAX_OFF, STATE_ADMIN, NATL_ADMIN
- **Query params**: `status` (pending/approved/rejected), `assigned_role`
- **Response**: `{ "items": [WorkflowTask...] }`

### POST /workflow/{taskId}/approve
Approve a workflow task (e.g. mutation approval). Writes audit log and publishes the next event in the chain.

- **Roles**: Determined by task type — mutation tasks: REV_OFF; tax tasks: TAX_OFF; zoning tasks: PLAN_OFF; plus STATE_ADMIN/NATL_ADMIN override.
- **Request body**: `{ "comment": "string" }`
- **Response 200**: `{ "task_id": int, "status": "approved", "next_event": "string|null" }`
- **Audit**: `action="APPROVE_MUTATION"` (or `APPROVE_<TASK_TYPE>`)
- **Event**: publishes `mutation.approved` -> Workflow Engine triggers Tax reassessment.

### POST /workflow/{taskId}/reject
Reject a workflow task with a reason.

- **Roles**: Same as approve.
- **Request body**: `{ "reason": "string" }`
- **Response 200**: `{ "task_id": int, "status": "rejected" }`
- **Audit**: `action="REJECT_MUTATION"`

### GET /workflow/events/stream
Server-Sent Events stream of cross-department sync events (live feed for the Sync Monitor). Polling fallback supported via `GET /workflow/events`.

- **Roles**: REV_OFF, REG_OFF, PLAN_OFF, TAX_OFF, STATE_ADMIN, NATL_ADMIN
- **Response**: `text/event-stream`; each event:
  ```json
  { "event": "registration.completed", "ulpin": "CH-UT-000002", "timestamp": "...", "actor": "reg_officer_chd" }
  ```

---

## Citizen Services

### POST /citizen/service-request
Citizen submits a service request (e.g. ownership certificate, mutation request, encumbrance certificate).

- **Roles**: CITIZEN
- **Request body**: `{ "ulpin": "string", "service_type": "OWNERSHIP_CERT|MUTATION_REQ|ENCUMBRANCE_CERT", "notes": "string" }`
- **Response 201**: `{ "request_id": "string", "status": "submitted" }`
- **Audit**: `action="CITIZEN_SERVICE_REQUEST"`

### GET /citizen/requests
List the citizen's own service requests.

- **Roles**: CITIZEN
- **Query params**: `status`
- **Response**: `{ "items": [ServiceRequest...] }`

### GET /citizen/parcels
List parcels the citizen owns (verified via name/ID match against RoR).

- **Roles**: CITIZEN
- **Response**: `{ "items": [ParcelPublic...] }`

---

## AI/ML

### POST /ml/change-detection
Upload before/after satellite images (multipart) for a parcel; returns detected change area and FAR violation flag update.

- **Roles**: PLAN_OFF, STATE_ADMIN, NATL_ADMIN
- **Request**: multipart `before_image`, `after_image`, form field `ulpin`
- **Response 200**: `{ "ulpin": "string", "changed_area_sqm": float, "far_existing_est": float, "violation_flag": bool }`
- **Side effect**: updates `zoning.far_existing` and `zoning.violation_flag`.
- **Audit**: `action="ML_CHANGE_DETECTION"`

### POST /ml/fraud-score
Score a registration transaction for fraud/anomaly (Isolation Forest).

- **Roles**: REG_OFF, STATE_ADMIN, NATL_ADMIN
- **Request body**: `{ "ulpin": "string", "deed_no": "string", "transaction_value": int }`
- **Response 200**: `{ "ulpin": "string", "deed_no": "string", "fraud_score": float, "flagged": bool }`
- **Audit**: `action="ML_FRAUD_SCORE"`

### POST /ml/ocr-extract
Upload a legacy RoR scan image; extract structured fields via OCR + regex.

- **Roles**: REV_OFF, STATE_ADMIN, NATL_ADMIN
- **Request**: multipart `image`, form field `state_code`
- **Response 200**: `{ "extracted": { "owner_name": "string", "survey_or_khasra_no": "string", "khatauni_no": "string" }, "confidence": float }`
- **Audit**: `action="ML_OCR_EXTRACT"`

---

## Admin

### GET /admin/state-adapter/{state_code}
Retrieve the State Adapter config for a state.

- **Roles**: STATE_ADMIN (own state only), NATL_ADMIN (all states)
- **Response**: `{ "items": [StateAdapterConfig...] }`

### PUT /admin/state-adapter/{state_code}
Update State Adapter field mapping / unit conversion for a state.

- **Roles**: NATL_ADMIN
- **Request body**: `StateAdapterConfigUpdate`
- **Response 200**: `StateAdapterConfig`
- **Audit**: `action="UPDATE_STATE_ADAPTER"`

### GET /admin/users
List all users (for admin dashboards).

- **Roles**: STATE_ADMIN (own jurisdiction), NATL_ADMIN
- **Response**: `{ "items": [UserInternal...] }` (passwords never returned)

---

## Analytics

### GET /analytics/national
National-level aggregate dashboard data (counts by state, violation counts, pending mutations, fraud flags).

- **Roles**: NATL_ADMIN
- **Response**: `{ "parcels_total": int, "by_state": {...}, "violations": int, "pending_mutations": int, "fraud_flags": int }`

### GET /analytics/state/{state_code}
State-level aggregate dashboard data.

- **Roles**: STATE_ADMIN (own state), NATL_ADMIN
- **Response**: `{ "parcels_total": int, "violations": int, "pending_mutations": int, "arrears_total": int }`

### GET /analytics/audit/{ulpin}
Retrieve the hash-chained audit trail for a parcel.

- **Roles**: All roles. CITIZEN sees a summary (actor_role + action + timestamp, no PII). Officers see full chain.
- **Response**: `{ "items": [AuditLogEntry...] }`

---

## Standard Response Envelope

Every JSON response (except the SSE stream and file downloads) is wrapped:

```json
{
  "success": true,
  "data": { ... },
  "errors": []
}
```

On error:

```json
{
  "success": false,
  "data": null,
  "errors": [
    { "code": "NOT_FOUND", "message": "Parcel CH-UT-999999 not found", "field": "ulpin" }
  ]
}
```

Standard error codes: `UNAUTHORIZED`, `FORBIDDEN`, `NOT_FOUND`, `VALIDATION_ERROR`, `CONFLICT`, `RATE_LIMITED`, `INTERNAL_ERROR`. HTTP status codes follow REST conventions (200/201/204 for success, 400/401/403/404/409/422/429/500 for errors). The envelope allows the frontend to parse success/data/errors uniformly.

---

## OpenAPI Export
The FastAPI app auto-generates `/openapi.json` (OpenAPI 3.1). This is exported to `/backend/openapi.yaml` and serves as the frozen contract between Track A and Track B (see docs/MULTI_AGENT_PARALLEL_WORKFLOW.md). The frontend codegen reads from this file — never hand-edit the frontend API types; regenerate from openapi.yaml.
