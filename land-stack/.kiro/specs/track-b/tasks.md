# Implementation Plan: Land Stack Track B -- React + Vite + TypeScript Frontend

## Tasks

- [x] 1. Project scaffold
  - [x] 1.1 package.json, vite.config.ts, tsconfig.json, index.html
  - [x] 1.2 src/main.tsx, src/App.tsx with all 16 routes
  - [x] 1.3 Zustand auth store, TanStack Query client, axios API client

- [x] 2. Shared components
  - [x] 2.1 TopNav, Footer, RoleRouteGuard
  - [x] 2.2 All 16 screen stubs created
  - [x] 2.3 Dockerfile, infra/nginx.conf, .github/workflows/ci.yml

- [ ] 3. Working login flows
  - [ ] 3.1 CitizenDashboard -- POST /auth/login form -> setAuth -> redirect by role
  - [ ] 3.2 OfficerLogin -- same flow for officer roles

- [ ] 4. Parcel 360 View (Screen 3)
  - [ ] 4.1 Tabbed view: Base / RoR / Registration / Encumbrance / Zoning / Tax
  - [ ] 4.2 Fetch each layer via TanStack Query
  - [ ] 4.3 Apply CITIZEN masking (partial owner_name, hidden transaction_value)

- [ ] 5. Ownership Verification (Screen 4)
  - [ ] 5.1 VerifyForm -> GET /ror/{ulpin} -> display masked result
  - [ ] 5.2 PDF download ownership certificate

- [ ] 6. GIS Map Explorer (Screen 2)
  - [ ] 6.1 MapLibre GL JS + pg_tileserv vector tile source
  - [ ] 6.2 LayerPanel: Base/Essential/Additional/Violation toggles + StateFilter
  - [ ] 6.3 Search -> GET /parcels/search, click parcel -> ParcelPreview sidebar

- [ ] 7. Citizen screens
  - [ ] 7.1 ServiceRequestPortal (5) -- POST /citizen/service-request
  - [ ] 7.2 RequestTracking (6) -- GET /citizen/requests

- [ ] 8. Officer screens
  - [ ] 8.1 OfficerDashboard (9) -- GET /workflow/tasks -> PendingTasksCard
  - [ ] 8.2 WorkflowApproval (10) -- Approve/Reject tasks

- [ ] 9. Zoning Dashboard (11) -- ViolationMap + ChangeDetectionPanel file upload
- [ ] 10. Sync Monitor (12) -- SSE connection to /workflow/events/stream
- [ ] 11. State Admin Panel (13) -- analytics + users + adapter view
- [ ] 12. National Analytics (14) -- Recharts BarChart + KPI row
- [ ] 13. Audit Trail Viewer (15) -- chain verification + SHA-256 recompute
- [ ] 14. API Explorer (16) -- Swagger UI embed from /openapi.json
