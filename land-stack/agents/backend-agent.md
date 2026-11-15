# Backend Agent (Track A — Fully Python / FastAPI)
Owns: all core service routers (parcel, ror, registration, encumbrance, zoning, building_permission, tax), workflow-engine (Redis pub/sub consumer), citizen services, and admin/state-adapter endpoints.

Must enforce:
- ULPIN as the join key in every SQLAlchemy model/query
- RBAC via Depends(require_role([...])) on every route, matching docs/RBAC_MATRIX.md
- Field-level masking via separate Pydantic "Public" vs "Internal" response schemas
- Audit log write before returning success on any write/approve action
- Pydantic schemas matching docs/DATA_SCHEMA.md
