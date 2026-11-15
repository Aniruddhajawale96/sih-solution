# Architecture

## 3-Layer Spatial Model

```
+-------------------------------------------------------------+
| ADDITIONAL LAYER (utilities, AI/ML overlays, analytics)     |
+-------------------------------------------------------------+
| ESSENTIAL LAYER (RoR, registration, encumbrance, zoning,    |
|   building permission, property tax)                        |
+-------------------------------------------------------------+
| BASE LAYER (cadastral parcel geometry, ULPIN, survey/       |
|   khasra no., admin boundaries)                             |
+-------------------------------------------------------------+
```

Every record in Essential/Additional layers references a parcel in the Base layer via ULPIN.

## System Architecture (prototype)

```
                    +-------------------+
                    |     Nginx (80)    |
                    +---------+---------+
                              |
          +-------------------+-------------------+
          |                                       |
+----------v----------+               +----------v----------+
| Frontend (React)    |               |  FastAPI Backend    |
| Vite + MapLibre     |<-- REST/JSON -|  (modular routers)  |
| port 3000           |               |  port 8000          |
+---------------------+               +----------+----------+
                                                 |
       +-----------+-----------+-----------------+-----------+
       |           |           |                             |
+------v------+ +--v----------+ +------v-------+ +----------v--+
| PostgreSQL+ | | Redis       | | MinIO        | | pg_tileserv |
| PostGIS     | | (pub/sub    | | (deeds,      | | (vector     |
| (all tables)| |  event bus) | |  certs, sat  | |  tiles)     |
+-------------+ +-------------+ |  images)     | +-------------+
                                 +--------------+
```

## Backend Module Boundaries
parcel, ror, registration, encumbrance, zoning, building_permission, tax, workflow_engine, citizen_services, admin — each has its own router file, its own Pydantic schemas, and is independently testable.

## Cross-Department Event Flow

```
Registration (REG_OFF registers deed)
  |
  v publish "registration.completed" event (Redis)
Workflow Engine
  |
  v creates mutation task for REV_OFF
Revenue Officer approves mutation
  |
  v publish "mutation.approved" event
Workflow Engine
  |
  v triggers Tax Service reassessment
Tax record updated -> visible instantly on citizen's Parcel 360 view
                   -> visible on Cross-Department Sync Monitor (live feed)
```

## State Adapter Pattern
Each state's raw source field names (e.g. Chandigarh's `Khasra_No`, `Owner_Nm` vs Tamil Nadu's `Survey_No`, `Pattathar_Peyar`) are mapped to canonical field names via `seed-data/state_adapter_config.json`, including a `unit_conversion_factor` (e.g. 4046.86 for acres -> sq.m). The backend never hardcodes a state's native field names in business logic — only in the adapter config.

## Security Boundary
```
Client --JWT (access+refresh)--> Nginx --> FastAPI
  FastAPI: Depends(get_current_user)
        -> Depends(require_role([...]))
        -> Depends(check_jurisdiction)
        -> Pydantic "Public" vs "Internal" response schema (field masking)
        -> audit_log write on mutation
```
