# Features — Land Stack (9 Modules)

Each module lists its feature IDs with acceptance criteria. Acceptance criteria are the source of truth for QA (agents/qa-docs-agent.md) and for the Definition of Done in AGENTS.md.

## Module F1 — GIS Parcel Core
### F1.1 Cadastral Map Rendering
- Acceptance: MapLibre renders parcel polygons from pg_tileserv vector tiles; pan/zoom smooth; clicking a parcel selects it and shows ULPIN in ParcelPreview.
### F1.2 3-Layer Toggle
- Acceptance: Base/Essential/Additional layers toggle independently; toggling off Base hides parcel polygons; violation overlay (Additional) shows only when enabled.
### F1.3 Parcel Search (spatial + attribute)
- Acceptance: Free-text search by ULPIN/Khasra/Survey No returns matches; bbox spatial search returns parcels within bounds; results paginated.

## Module F2 — Parcel 360 / Data Integration
### F2.1 Unified Parcel 360 View
- Acceptance: Single view joins parcel + ror + registration + encumbrance + zoning + tax under one ULPIN; tabs switch layers; masking applied per role.
### F2.2 Cross-Record Join Integrity
- Acceptance: Every Essential/Additional record shown resolves to the same parcel via ULPIN; no orphan records in seed data.

## Module F3 — State Adapter / Interoperability
### F3.1 Field Mapping
- Acceptance: Chandigarh `Khasra_No`/`Owner_Nm` and Tamil Nadu `Survey_No`/`Pattathar_Peyar` both map to canonical `survey_or_khasra_no`/`owner_name` via state_adapter_config; backend never hardcodes native names.
### F3.2 Unit Conversion
- Acceptance: Tamil Nadu `area_acres` converts to canonical `area_sqm` using factor 4046.86; Chandigarh already-sqm passes through with factor 1; displayed area always sq.m.

## Module F4 — Workflow Automation
### F4.1 Registration → Mutation Auto-Task
- Acceptance: A new registration publishes `registration.completed`; Workflow Engine creates a mutation task assigned to REV_OFF; visible in TaskQueue.
### F4.2 Mutation Approval → Tax Reassessment
- Acceptance: REV_OFF approving a mutation publishes `mutation.approved`; Tax Service reassesses; updated tax visible instantly on Parcel 360 and Sync Monitor.
### F4.3 Live Sync Monitor
- Acceptance: Sync Monitor shows the full event chain (registration→mutation→tax) in real time via SSE/polling; each event shows actor, ulpin, timestamp.

## Module F5 — Citizen Services
### F5.1 Service Request Submission
- Acceptance: Citizen submits Ownership Cert / Mutation / Encumbrance Cert request for a ULPIN; system stores + assigns to officer queue.
### F5.2 Request Tracking
- Acceptance: Citizen sees status timeline of their own requests; officer comments visible when present.
### F5.3 Ownership Verification (public)
- Acceptance: Public user verifies current owner (masked) + tenure + mutation status for a ULPIN; downloadable certificate generated.

## Module F6 — AI / ML
### F6.1 Change Detection (FAR violations)
- Acceptance: Upload before/after satellite images; system returns changed area + estimated FAR; updates `zoning.far_existing` and sets `violation_flag`; appears on Zoning Dashboard.
### F6.2 Fraud / Anomaly Scoring
- Acceptance: Score a registration transaction; returns fraud_score + flagged boolean; high-score deeds flagged for REG_OFF review.
### F6.3 OCR Digitization
- Acceptance: Upload legacy RoR scan; system extracts owner_name, survey_or_khasra_no, khatauni_no with a confidence score; officer can review/confirm.

## Module F7 — Security & Audit
### F7.1 RBAC Enforcement
- Acceptance: Every route enforces role + jurisdiction; a CITIZEN cannot reach officer-only endpoints; a TN officer cannot read CH records; masked fields verified in responses.
### F7.2 Hash-Chained Audit Log
- Acceptance: Every write/approve writes an audit_log row; `hash` = SHA-256(prev_hash + row); Audit Trail Viewer verifies chain integrity; tampering with any row breaks the chain.
### F7.3 Field-Level Masking
- Acceptance: Public schema masks owner_name (partial), owner_id_ref (full), transaction_value (hidden), shows encumbrance.institution + tax.arrears; matches docs/RBAC_MATRIX.md.

## Module F8 — Admin & Analytics
### F8.1 State Admin Panel
- Acceptance: STATE_ADMIN sees cross-department summary + user list scoped to own state; cannot see other states' data.
### F8.2 National / DoLR Analytics
- Acceptance: NATL_ADMIN sees national aggregates (parcels, violations, pending mutations, fraud flags) by state; charts render; State Adapter config editable.

## Module F9 — Documentation Deliverable
### F9.1 Standard Technical Document
- Acceptance: Compiled from docs/*.md + exported openapi.yaml; covers API standards, interoperability, data schemas, architecture, GIS standards, security, UI/UX guidelines, deployment/scalability; delivered as a single navigable document.
