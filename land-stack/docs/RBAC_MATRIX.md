# RBAC Matrix — Land Stack

7 roles, enforced server-side on every route via `Depends(require_role([...]))` plus a jurisdiction check (`check_jurisdiction`). The frontend must mirror this exactly — it never invents its own role logic; it only reflects what the backend allows. Officers are scoped to their `jurisdiction` state_code (or null for NATL_ADMIN / CITIZEN who see all states in public form).

## Permission Legend
| Symbol | Meaning |
|---|---|
| R | Read — full/internal view of the resource |
| W | Write — create or update the resource |
| A | Approve — approve a workflow task on this resource |
| X | Execute — run an ML/action endpoint against this resource |
| R* | Read with masking — public/partially-masked view only |
| — | No access |

## The 7 Roles

| Role code | Full name | Jurisdiction | Purpose |
|---|---|---|---|
| CITIZEN | Citizen | null (all states, public view) | Verify ownership, self-service, track requests |
| REV_OFF | Revenue Officer | one state_code | RoR custody, mutation approval |
| REG_OFF | Registration Officer | one state_code | Deed registration, encumbrance entry |
| PLAN_OFF | Planning Officer | one state_code | Master plan/zoning, building permission, FAR |
| TAX_OFF | Tax Officer | one state_code | Property tax assessment/reassessment |
| STATE_ADMIN | State Administrator | one state_code | Cross-department oversight within a state |
| NATL_ADMIN | National Administrator (DoLR) | null (all states) | National oversight, State Adapter config, analytics |

## Resource × Role Permission Matrix

16 resource types. Each cell is the set of permissions that role holds on that resource, scoped to the role's jurisdiction where applicable.

| # | Resource | CITIZEN | REV_OFF | REG_OFF | PLAN_OFF | TAX_OFF | STATE_ADMIN | NATL_ADMIN |
|---|---|---|---|---|---|---|---|---|
| 1 | parcel (cadastral geometry) | R* | R, W | R | R | R | R, W | R, W |
| 2 | ror (Record of Rights) | R* | R, W, A | R | R | R | R, W, A | R, W, A |
| 3 | registration (deeds) | R* | R | R, W | R | R | R, W | R, W |
| 4 | encumbrance | R | R | R, W | R | R | R, W | R, W |
| 5 | zoning (master plan/FAR) | R | R | R | R, W, A | R | R, W, A | R, W, A |
| 6 | building_permission | R | R | R | R, W | R | R, W | R, W |
| 7 | tax (assessment/arrears) | R* | R | R | R | R, W, A | R, W, A | R, W, A |
| 8 | audit_log | R* | R | R | R | R | R | R |
| 9 | state_adapter_config | — | R | R | R | R | R (own) | R, W, A |
| 10 | workflow_tasks | — | R, A | R | R, A | R, A | R, A | R, A |
| 11 | citizen_service_requests | R, W | R, A | R | R, A | R, A | R, A | R, A |
| 12 | ml_change_detection | — | — | — | X | — | X | X |
| 13 | ml_fraud_score | — | — | X | — | — | X | X |
| 14 | ml_ocr_extract | — | X | — | — | — | X | X |
| 15 | users (admin management) | — | — | — | — | — | R (own) | R, W |
| 16 | analytics | — | — | — | — | — | R (own) | R |

Notes:
- CITIZEN `citizen_service_requests` = W (submit) + R (own requests only); officer `A` = approve/fulfill the request.
- `A` on `workflow_tasks` is constrained by task type: mutation tasks → REV_OFF, zoning tasks → PLAN_OFF, tax tasks → TAX_OFF; STATE_ADMIN/NATL_ADMIN may approve any task type as override.
- STATE_ADMIN scope is limited to records whose parcel `state_code` matches the admin's jurisdiction; NATL_ADMIN has no jurisdiction restriction.

## Field-Level Masking Rules

Applied by selecting the `Public` vs `Internal` Pydantic response schema based on caller role. Masking is applied on the backend; the frontend only renders what it receives.

| Field | Resource | CITIZEN (public) | Officers (non-owner dept) | Owner-dept officer | STATE_ADMIN | NATL_ADMIN |
|---|---|---|---|---|---|---|
| owner_name | ror | Partial mask — `Ramesh K***` | Full | Full | Full | Full |
| owner_id_ref | ror | Fully masked — `********` | Fully masked | Full | Full | Full |
| transaction_value | registration | Hidden (omitted) | Hidden | Full (REG_OFF) | Full | Full |
| buyer / seller | registration | Partial mask — `Priya S***` / `Vikram S***` | Full | Full | Full | Full |
| encumbrance.institution | encumbrance | Shown (public) | Shown | Shown | Shown | Shown |
| encumbrance.status | encumbrance | Shown (public) | Shown | Shown | Shown | Shown |
| tax.arrears | tax | Shown (public interest) | Shown | Shown | Shown | Shown |
| tax.annual_tax | tax | Hidden (omitted) | Full | Full | Full | Full |
| tax.payment_status | tax | Shown | Shown | Shown | Shown | Shown |
| parcel.geom | parcel | Centroid + area only (no full polygon) | Full | Full | Full | Full |
| audit_log.actor_user | audit_log | Masked to role only | Full | Full | Full | Full |
| audit_log.actor_role | audit_log | Shown | Shown | Shown | Shown | Shown |
| audit_log.action | audit_log | Shown | Shown | Shown | Shown | Shown |
| audit_log.hash / prev_hash | audit_log | Hidden | Shown | Shown | Shown | Shown |

Masking rules in plain language:
1. **owner_name** is partially masked for citizens (first name + first letter of surname + `***`).
2. **owner_id_ref** (any national ID reference) is fully masked for citizens and for officers outside the owning department; only owner-department officers and admins see it.
3. **transaction_value** is hidden from the public entirely; visible only to REG_OFF, STATE_ADMIN, NATL_ADMIN.
4. **encumbrance.institution** is always shown publicly — transparency requirement for prospective buyers/lenders.
5. **tax.arrears** is always shown publicly — public interest in flagging defaulters. `tax.annual_tax` is hidden from the public but shown to officers.

## API Endpoint → Role Mapping

| Method | Endpoint | Allowed roles | Masking |
|---|---|---|---|
| POST | /auth/login | Public | n/a |
| POST | /auth/refresh | Any | n/a |
| POST | /auth/logout | Any | n/a |
| GET | /parcels/{ulpin} | All | R* for CITIZEN |
| GET | /parcels/search | All | R* for CITIZEN |
| POST | /parcels | REV_OFF, STATE_ADMIN, NATL_ADMIN | Internal |
| GET | /ror/{ulpin} | All | R* for CITIZEN |
| PUT | /ror/{ulpin} | REV_OFF, STATE_ADMIN, NATL_ADMIN | Internal |
| POST | /registration | REG_OFF, STATE_ADMIN, NATL_ADMIN | Internal |
| GET | /registration | All | R* for CITIZEN/REV_OFF |
| GET | /registration/{id} | All | R* for CITIZEN/REV_OFF |
| POST | /encumbrance | REG_OFF, STATE_ADMIN, NATL_ADMIN | Internal |
| GET | /encumbrance/{ulpin} | All | Public (no masking) |
| PUT | /zoning/{ulpin} | PLAN_OFF, STATE_ADMIN, NATL_ADMIN | Internal |
| GET | /zoning/{ulpin} | All | Public (no masking) |
| POST | /building-permission | PLAN_OFF, STATE_ADMIN, NATL_ADMIN | Internal |
| GET | /building-permission/{ulpin} | All | Public |
| GET | /tax/{ulpin} | All | R* for CITIZEN |
| PUT | /tax/{ulpin} | TAX_OFF, STATE_ADMIN, NATL_ADMIN | Internal |
| GET | /workflow/tasks | REV_OFF, REG_OFF, PLAN_OFF, TAX_OFF, STATE_ADMIN, NATL_ADMIN | Internal |
| POST | /workflow/{taskId}/approve | REV_OFF/PLAN_OFF/TAX_OFF (by task type), STATE_ADMIN, NATL_ADMIN | Internal |
| POST | /workflow/{taskId}/reject | same as approve | Internal |
| GET | /workflow/events/stream | All officers + admins | Internal |
| POST | /citizen/service-request | CITIZEN | Internal (own) |
| GET | /citizen/requests | CITIZEN | Internal (own) |
| GET | /citizen/parcels | CITIZEN | R* |
| POST | /ml/change-detection | PLAN_OFF, STATE_ADMIN, NATL_ADMIN | Internal |
| POST | /ml/fraud-score | REG_OFF, STATE_ADMIN, NATL_ADMIN | Internal |
| POST | /ml/ocr-extract | REV_OFF, STATE_ADMIN, NATL_ADMIN | Internal |
| GET | /admin/state-adapter/{state_code} | STATE_ADMIN (own), NATL_ADMIN | Internal |
| PUT | /admin/state-adapter/{state_code} | NATL_ADMIN | Internal |
| GET | /admin/users | STATE_ADMIN (own), NATL_ADMIN | Internal |
| GET | /analytics/national | NATL_ADMIN | Internal |
| GET | /analytics/state/{state_code} | STATE_ADMIN (own), NATL_ADMIN | Internal |
| GET | /analytics/audit/{ulpin} | All | R* for CITIZEN |
