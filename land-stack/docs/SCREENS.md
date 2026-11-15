# Screens — Land Stack (16 Screens)

7 Public/Citizen screens, 7 Officer/Admin screens, 2 Shared screens. Wireframes for each are in docs/WIREFRAMES.md. Role-based routing enforces access per docs/RBAC_MATRIX.md.

## Public / Citizen Screens (7)

| # | Screen | Route | Roles | Purpose |
|---|---|---|---|---|
| 1 | Landing Page | `/` | Public | Project intro, "Verify a parcel" CTA, citizen login entry |
| 2 | GIS Map Explorer | `/map` | Public | Pan/zoom cadastral map, layer toggle (3-layer model), click parcel → preview |
| 3 | Parcel 360 View | `/parcel/{ulpin}` | Public (masked) | Unified view of all layers for one ULPIN; masked for citizen, full for officers |
| 4 | Ownership Verification | `/parcel/{ulpin}/verify` | Public | Verify current owner + tenure + mutation status; downloadable ownership certificate |
| 5 | Service Request Portal | `/citizen/services` | CITIZEN | Submit service requests (ownership cert, mutation, encumbrance cert) |
| 6 | Request Tracking | `/citizen/requests` | CITIZEN | Track status of submitted service requests |
| 7 | Citizen Login / Dashboard | `/citizen/dashboard` | CITIZEN | Citizen auth + personal dashboard (owned parcels, requests) |

## Officer / Admin Screens (7)

| # | Screen | Route | Roles | Purpose |
|---|---|---|---|---|
| 8 | Officer Login | `/officer/login` | Officers | Officer auth; routes to role-specific dashboard |
| 9 | Officer Dashboard | `/officer/dashboard` | REV_OFF, REG_OFF, PLAN_OFF, TAX_OFF | Pending tasks count, recent activity, quick actions |
| 10 | Mutation / Approval Workflow | `/officer/workflow` | REV_OFF, PLAN_OFF, TAX_OFF, STATE_ADMIN | Queue of pending workflow tasks; approve/reject mutation, zoning, tax tasks |
| 11 | Zoning & Violation Dashboard | `/officer/zoning` | PLAN_OFF, STATE_ADMIN | Map + table of FAR violations from ML change detection; update zoning |
| 12 | Cross-Department Sync Monitor | `/officer/sync` | All officers | Real-time SSE/polling feed of cross-department events (registration→mutation→tax) |
| 13 | State Admin Panel | `/admin/state` | STATE_ADMIN | Cross-department oversight for one state; user mgmt, adapter view |
| 14 | National / DoLR Analytics Dashboard | `/admin/national` | NATL_ADMIN | National aggregates, fraud flags, violations, State Adapter config editor |

## Shared Screens (2)

| # | Screen | Route | Roles | Purpose |
|---|---|---|---|---|
| 15 | Audit Trail Viewer | `/audit/{ulpin}` | All (masked for citizen) | Hash-chained audit log for a parcel; verify chain integrity |
| 16 | API Explorer | `/api-explorer` | All | Interactive OpenAPI/Swagger UI; role-aware request testing |

## Routing & Guards
- Public screens (1–4) are accessible without login, but data is masked (R*).
- Citizen screens (5–7) require CITIZEN auth.
- Officer screens (8–14) require the listed officer/admin roles; jurisdiction filter applied.
- Shared screens (15–16) adapt content by role (citizen sees masked audit summary; officers see full chain).
- A `RoleRouteGuard` component wraps protected routes and reads the role from the Zustand auth store (populated from `/auth/login` response).
