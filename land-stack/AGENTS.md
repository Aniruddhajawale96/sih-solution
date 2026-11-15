# AGENTS.md — Land Stack Project (Root Entry Point)

Read this file first, always, before touching any code.

## What this project is
Land Stack is a GIS-based Digital Public Infrastructure for Land Governance, built for SIH Problem Statement #26014 (Ministry of Rural Development, Department of Land Resources). It unifies cadastral maps, Record of Rights (RoR), registration, encumbrance, master plan/zoning, building permission, property tax, and utilities into one ULPIN-anchored, interoperable platform. Two pilots: Chandigarh (urban) and a Tamil Nadu village (rural).

## Golden Rules (never violate these)
1. ULPIN is the universal join key across every table and every API response.
2. Never hardcode state-specific field names, units, or language strings — always go through the State Adapter config (docs/DATA_SCHEMA.md, seed-data/state_adapter_config.json).
3. Every resource follows the 3-layer GIS model: Base (cadastral geometry), Essential (ownership/registration/zoning/tax), Additional (utilities/ML insights). Never collapse these layers together in the UI or schema.
4. RBAC is enforced server-side on every route — 7 roles, see docs/RBAC_MATRIX.md. The frontend must mirror this exactly, never invent its own role logic.
5. Every write/approve action must produce an audit_log entry before returning success (hash-chained, see docs/DATA_SCHEMA.md).
6. Backend is 100% Python (FastAPI). Do not introduce Node.js/Express for backend logic under any circumstance.
7. Treat docs/*.md as living contracts. If you change a schema or API shape, update the relevant doc in the same commit/PR.
8. Never summarize or compress existing detailed documentation when regenerating files — full detail must always be preserved verbatim.

## Tech Stack Summary
- Frontend: React 18 + Vite + TypeScript, TailwindCSS + shadcn/ui, MapLibre GL JS, Zustand, TanStack Query, Recharts
- Backend: FastAPI (Python), SQLAlchemy 2.0 + GeoAlchemy2, Alembic, Pydantic v2, python-jose + passlib[bcrypt], redis-py pub/sub, Uvicorn
- AI/ML: OpenCV, scikit-learn, pytesseract — same Python runtime as backend
- DB/GIS: PostgreSQL 16 + PostGIS, pg_tileserv, MinIO
- DevOps: Docker Compose (prototype), GitHub Actions

## Sub-Agent Directory
| File | Track | Owns |
|---|---|---|
| agents/orchestrator-agent.md | Shared | Task breakdown, roadmap, sync log |
| agents/backend-agent.md | A | Core FastAPI routers |
| agents/database-agent.md | A | PostGIS schema, migrations, seed loaders |
| agents/ai-ml-agent.md | A | Change detection, fraud score, OCR |
| agents/security-agent.md | A | Auth, RBAC enforcement, audit log, masking |
| agents/frontend-agent.md | B | All 16 screens (React) |
| agents/gis-agent.md | B | Map rendering, layer toggle, tile styling |
| agents/devops-agent.md | B | Docker Compose, Nginx, CI |
| agents/qa-docs-agent.md | Shared | Testing, final doc compilation, demo rehearsal |

## Definition of Done (per feature)
- [ ] Code matches the exact schema in docs/DATA_SCHEMA.md
- [ ] RBAC enforced per docs/RBAC_MATRIX.md (role + jurisdiction + field masking)
- [ ] Audit log entry written for every write/approve action
- [ ] Endpoint documented in docs/API_SPEC.md (or auto-reflected in openapi.yaml)
- [ ] Works against seed-data/*, demoable via docker-compose up
- [ ] Relevant docs/*.md updated in the same PR
- [ ] docs/SYNC_LOG.md updated if the change affects the other track
