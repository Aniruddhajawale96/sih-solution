# Roadmap — Land Stack

Checklists per track. Updated by the Orchestrator. See docs/MULTI_AGENT_PARALLEL_WORKFLOW.md for the parallel-work contract.

## Track A — Backend (Python / FastAPI)
- [ ] Scaffold FastAPI app (`main.py`) with router aggregation + standard response envelope
- [ ] Database Agent: SQLAlchemy 2.0 + GeoAlchemy2 models for all tables in docs/DATA_SCHEMA.md
- [ ] Database Agent: Alembic initial migration + upgrade/downgrade
- [ ] Database Agent: seed loader scripts (chandigarh_parcels, tn_village_parcels, ror, registration, encumbrance, zoning, building_permission, tax, users, state_adapter_config)
- [ ] Security Agent: JWT auth (access + refresh) via python-jose + passlib
- [ ] Security Agent: RBAC dependencies (`get_current_user`, `require_role`, `check_jurisdiction`)
- [ ] Security Agent: hash-chained audit log (`core/audit.py`) with prev_hash chaining
- [ ] Security Agent: Pydantic Public vs Internal response schemas (field masking)
- [ ] Backend Agent: parcel router (GET /parcels/{ulpin}, GET /parcels/search, POST /parcels)
- [ ] Backend Agent: ror router (GET /ror/{ulpin}, PUT /ror/{ulpin})
- [ ] Backend Agent: registration router (POST /registration, GET /registration, GET /registration/{id})
- [ ] Backend Agent: encumbrance router (POST /encumbrance, GET /encumbrance/{ulpin})
- [ ] Backend Agent: zoning router (PUT /zoning/{ulpin}, GET /zoning/{ulpin})
- [ ] Backend Agent: building_permission router (POST, GET)
- [ ] Backend Agent: tax router (GET /tax/{ulpin}, PUT /tax/{ulpin})
- [ ] Backend Agent: workflow_engine (Redis pub/sub consumer) — registration.completed → mutation task; mutation.approved → tax reassessment
- [ ] Backend Agent: workflow router (GET /workflow/tasks, POST /workflow/{id}/approve, POST /workflow/{id}/reject, GET /workflow/events/stream)
- [ ] Backend Agent: citizen_services router (POST /citizen/service-request, GET /citizen/requests, GET /citizen/parcels)
- [ ] Backend Agent: admin router (GET/PUT /admin/state-adapter, GET /admin/users)
- [ ] Backend Agent: analytics router (GET /analytics/national, /analytics/state/{code}, /analytics/audit/{ulpin})
- [ ] AI/ML Agent: change_detection.py (OpenCV) + /ml/change-detection route
- [ ] AI/ML Agent: fraud_score.py (Isolation Forest) + /ml/fraud-score route
- [ ] AI/ML Agent: ocr_extraction.py (pytesseract) + /ml/ocr-extract route
- [ ] Export openapi.yaml (frozen contract for Track B)
- [ ] pytest suites per router (httpx TestClient) — green

## Track B — Frontend (React + Vite + TS)
- [ ] DevOps Agent: docker-compose.yml final (postgres, pg_tileserv, redis, minio, backend, frontend)
- [ ] DevOps Agent: Nginx reverse proxy config (frontend :3000 + backend :8000)
- [ ] DevOps Agent: GitHub Actions CI (eslint + tsc frontend, pytest + ruff backend)
- [ ] Frontend Agent: Vite + React + TS scaffold; TailwindCSS + shadcn/ui setup
- [ ] Frontend Agent: Zustand auth store (role + jurisdiction from /auth/login)
- [ ] Frontend Agent: TanStack Query client + openapi.yaml codegen for API types
- [ ] Frontend Agent: RoleRouteGuard + role-based routing for all 7 roles
- [ ] Frontend Agent: Screen 1 Landing Page
- [ ] Frontend Agent: Screen 3 Parcel 360 View (tabs per layer, masked fields)
- [ ] Frontend Agent: Screen 4 Ownership Verification (+ PDF cert)
- [ ] Frontend Agent: Screen 5 Service Request Portal
- [ ] Frontend Agent: Screen 6 Request Tracking
- [ ] Frontend Agent: Screen 7 Citizen Login / Dashboard
- [ ] Frontend Agent: Screen 8 Officer Login
- [ ] Frontend Agent: Screen 9 Officer Dashboard
- [ ] Frontend Agent: Screen 10 Mutation / Approval Workflow
- [ ] Frontend Agent: Screen 12 Cross-Department Sync Monitor (SSE/polling live feed)
- [ ] Frontend Agent: Screen 13 State Admin Panel
- [ ] Frontend Agent: Screen 14 National / DoLR Analytics Dashboard (Recharts)
- [ ] Frontend Agent: Screen 15 Audit Trail Viewer
- [ ] Frontend Agent: Screen 16 API Explorer (Swagger UI)
- [ ] Frontend Agent: field-level masking display logic matching RBAC_MATRIX.md
- [ ] GIS Agent: MapLibre integration + pg_tileserv vector tile source
- [ ] GIS Agent: Screen 2 GIS Map Explorer (layer toggle, state filter, search)
- [ ] GIS Agent: Screen 11 Zoning & Violation Dashboard (violation map + change detection upload)
- [ ] GIS Agent: CRS alignment checks (EPSG:4326), layer toggle behavior for 3-layer model
- [ ] eslint + tsc green

## Shared
- [ ] Freeze contract: openapi.yaml, DATA_SCHEMA.md, seed-data/*, RBAC_MATRIX.md
- [ ] docs/SYNC_LOG.md updated at each sync cadence
- [ ] QA/Docs Agent: pytest walkthroughs for each backend feature
- [ ] QA/Docs Agent: manual test walkthroughs for each frontend screen
- [ ] QA/Docs Agent: `docker-compose up` from fresh clone works end-to-end
- [ ] QA/Docs Agent: Standard Technical Document compiled from docs/*.md + openapi.yaml
- [ ] QA/Docs Agent: demo script rehearsal (Workflow B core demo)
- [ ] Pitch deck / demo script finalized
