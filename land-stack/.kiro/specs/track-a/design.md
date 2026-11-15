# Design Document — Land Stack Track A (Backend)

## Overview

Track A is a Python/FastAPI service that persists all land-governance data in PostgreSQL/PostGIS and exposes a REST API consumed by the React frontend (Track B). The design is derived directly from the frozen contracts in `docs/`; this document translates those contracts into concrete module boundaries, interface signatures, and data-flow decisions.

**Language / Runtime**: Python 3.11, FastAPI 0.115, SQLAlchemy 2.0 async, GeoAlchemy2, Alembic, Redis, OpenCV, scikit-learn, pytesseract, python-jose, passlib.

---

## Architecture

```
backend/
  main.py                  # FastAPI app, router registration, lifespan
  core/
    database.py            # SQLAlchemy async engine + session dependency
    auth.py                # JWT creation/validation, token blacklist (Redis)
    rbac.py                # get_current_user, require_role, check_jurisdiction
    audit.py               # hash-chain writer
    schemas.py             # shared Pydantic bases + envelope
  models/                  # one file per table (SQLAlchemy DeclarativeBase)
  routers/                 # one file per domain (FastAPI APIRouter)
  ml/                      # OpenCV / Isolation Forest / pytesseract scripts
  workflow_engine/
    consumer.py            # asyncio Redis subscriber
  alembic/                 # env.py + versions/
  scripts/
    seed_loader.py
  tests/
  Dockerfile
  alembic.ini
```

All contract detail lives in `docs/`; the design sections below provide implementation guidance only.

---

## Component Designs

### 1. `core/database.py`

```python
# SQLAlchemy 2.0 async engine
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

engine = create_async_engine(settings.DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
```

The `DATABASE_URL` is read from an environment variable (`postgresql+asyncpg://...`). Tests override it with an in-memory or test-schema URL.

---

### 2. `core/auth.py`

Responsibilities:
- `create_access_token(data, expires_delta)` → signed HS256 JWT (15 min)
- `create_refresh_token(data)` → signed HS256 JWT (7 days)
- `verify_token(token)` → decoded payload or raises `HTTPException(401)`
- `blacklist_token(jti, redis_client)` → `SET jti 1 EX <remaining_ttl>`
- `is_blacklisted(jti, redis_client)` → bool

Token payload: `{ sub: username, role: role_code, jurisdiction: state_code|null, jti: uuid4 }`.

---

### 3. `core/rbac.py`

```python
def get_current_user(token=Depends(oauth2_scheme), db=Depends(get_db)) -> UserClaims:
    ...

def require_role(roles: list[str]) -> Callable:
    def dependency(user=Depends(get_current_user)):
        if user.role not in roles:
            raise HTTPException(403, ...)
    return Depends(dependency)

def check_jurisdiction(ulpin: str, user=Depends(get_current_user), db=Depends(get_db)):
    # Look up parcel.state_code; compare to user.jurisdiction
    # Roles with null jurisdiction (CITIZEN, NATL_ADMIN) always pass
    ...
```

Every route that touches parcel-scoped data chains: `Depends(require_role([...]))` → `Depends(check_jurisdiction)`.

---

### 4. `core/audit.py`

```python
async def write_audit(
    db: AsyncSession,
    actor_user: str,
    actor_role: str,
    action: str,
    resource_type: str,
    resource_id: str,
) -> AuditLog:
    last = await db.execute(select(AuditLog).order_by(AuditLog.id.desc()).limit(1))
    prev_hash = last.scalar_one_or_none()?.hash or "0" * 64
    row_content = f"{actor_user}{actor_role}{action}{resource_type}{resource_id}{timestamp}"
    new_hash = sha256((prev_hash + row_content).encode()).hexdigest()
    entry = AuditLog(prev_hash=prev_hash, hash=new_hash, ...)
    db.add(entry)
    await db.flush()   # get the id before the outer transaction commits
    return entry
```

`write_audit` is called inside the same DB transaction as the mutation, before `await db.commit()`. If the commit fails, the audit row is also rolled back — no orphan audit entries.

---

### 5. `core/schemas.py` — Envelope + Shared Bases

```python
class ErrorDetail(BaseModel):
    code: str
    message: str
    field: str | None = None

class Envelope(BaseModel, Generic[T]):
    success: bool
    data: T | None
    errors: list[ErrorDetail] = []

def ok(data) -> Envelope:
    return Envelope(success=True, data=data)

def err(code, message, field=None) -> Envelope:
    return Envelope(success=False, data=None,
                    errors=[ErrorDetail(code=code, message=message, field=field)])
```

All routers return `Envelope[<schema>]`; FastAPI serializes via `response_model=Envelope[...]`.

---

### 6. Models (`models/`)

One file per table. All inherit from `Base = DeclarativeBase()` defined in `core/database.py`.

Key implementation notes:
- `parcel.geom` → `Column(Geometry("POLYGON", srid=4326))`
- All string PKs/FKs are `String`, not UUID, matching the ULPIN format (`CH-UT-000001`).
- `audit_log.id` is an `Integer` autoincrement PK; every other table uses `ulpin` as the natural key (with `registration` and `workflow_tasks` adding integer surrogate PKs for list lookups).
- `workflow_tasks` has fields: `id` (int PK), `ulpin`, `task_type` (MUTATION/TAX/ZONING), `assigned_role`, `status` (pending/approved/rejected), `created_at`, `resolved_at`, `comment`.
- `citizen_service_requests` has: `id` (UUID string PK), `ulpin`, `citizen_username`, `service_type`, `notes`, `status`, `created_at`.

---

### 7. Alembic (`alembic/`)

`alembic/env.py` imports `Base.metadata` from `core/database.py` and uses `run_async_migrations()` with the asyncpg driver. The initial migration `versions/001_initial.py` creates all 11 tables including PostGIS extension (`CREATE EXTENSION IF NOT EXISTS postgis`).

---

### 8. Routers (`routers/`)

Pattern applied to every router file:

```python
router = APIRouter(prefix="/resource", tags=["Resource"])

@router.get("/{ulpin}", response_model=Envelope[ResourcePublic | ResourceInternal])
async def get_resource(
    ulpin: str,
    user: UserClaims = Depends(get_current_user),
    _role = Depends(require_role(["CITIZEN", "REV_OFF", ...])),
    _jx = Depends(check_jurisdiction),
    db: AsyncSession = Depends(get_db),
):
    record = await db.get(Resource, ulpin)
    if not record:
        raise HTTPException(404, ...)
    schema = ResourcePublic if user.role == "CITIZEN" else ResourceInternal
    return ok(schema.model_validate(record))
```

Write endpoints additionally call `await write_audit(...)` inside the same transaction before `await db.commit()`.

---

### 9. `workflow_engine/consumer.py`

Runs as an `asyncio` background coroutine started in `main.py`'s lifespan context. Subscribes to Redis channels `registration.completed` and `mutation.approved`.

```
registration.completed → create workflow_tasks row (type=MUTATION, role=REV_OFF)
mutation.approved       → update tax record + write audit row (action=REASSESS_TAX)
```

The workflow router's `GET /workflow/events/stream` endpoint also reads from Redis to deliver SSE events.

---

### 10. ML Modules (`ml/`)

| File | Library | Input | Output |
|---|---|---|---|
| `change_detection.py` | OpenCV | 2 images (bytes), ulpin | `{changed_area_sqm, far_existing_est, violation_flag}` |
| `fraud_score.py` | scikit-learn IsolationForest | transaction dict | `{fraud_score, flagged}` |
| `ocr_extraction.py` | pytesseract | image bytes, state_code | `{extracted: {...}, confidence}` |

Models are loaded at module import (singleton). The Isolation Forest model is trained on the seed `registration.json` data at startup if no persisted model file is found.

---

### 11. `scripts/seed_loader.py`

Reads each seed file from `../seed-data/`, applies the State Adapter mapping from `state_adapter_config.json`, then upserts rows using SQLAlchemy `on_conflict_do_update` on the ULPIN (or appropriate PK). GeoJSON parcels are inserted with `ST_GeomFromGeoJSON(geometry_str)`.

---

### 12. `Dockerfile`

```dockerfile
FROM python:3.11-slim
RUN apt-get install -y libgdal-dev tesseract-ocr
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## Data Flow — Write Path (example: POST /registration)

```
Client POST /registration
  → Nginx → FastAPI
  → Depends(get_current_user)       # decode JWT
  → Depends(require_role(["REG_OFF","STATE_ADMIN","NATL_ADMIN"]))
  → Depends(check_jurisdiction)     # parcel.state_code matches user.jurisdiction
  → router handler
      → db.add(Registration(...))
      → write_audit(action="REGISTER_DEED")
      → db.commit()
      → redis.publish("registration.completed", payload)
  → return Envelope[RegistrationInternal]

Workflow Engine (background)
  → receives "registration.completed"
  → db.add(WorkflowTask(type=MUTATION, ...))
  → db.commit()
```

---

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system — essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Audit log entry exists after every write

For any successful write or approve action (POST, PUT, approve), the `audit_log` table SHALL contain a new row with `resource_id` equal to the ULPIN of the modified record and `action` matching the documented action string, before the HTTP response is returned.

**Validates: Requirements 6.1, 6.2**

### Property 2: Hash chain integrity

For any two consecutive `audit_log` rows with ids N and N+1, `row[N+1].prev_hash` SHALL equal `row[N].hash`, and `row[N+1].hash` SHALL equal SHA-256(`row[N].hash` + serialized row N+1 contents).

**Validates: Requirements 6.2, 6.3**

### Property 3: Role enforcement — forbidden access

For any endpoint E and any caller whose role is not in E's allowed-role list (per `docs/RBAC_MATRIX.md`), the System SHALL return HTTP 403 and SHALL NOT modify any database row.

**Validates: Requirements 5.2, 5.3**

### Property 4: Response envelope invariant

For any HTTP response from the System (except SSE streams), the response body SHALL be a valid JSON object containing the keys `success` (bool), `data` (any or null), and `errors` (array).

**Validates: Requirements 1.2**

### Property 5: Field masking — CITIZEN never receives hidden fields

For any response returned to a CITIZEN-role caller, the response body SHALL NOT contain the fields `transaction_value`, `owner_id_ref`, `audit_log.hash`, `audit_log.prev_hash`, or the full parcel polygon geometry.

**Validates: Requirements 7.2, 7.4, 7.5**

### Property 6: Jurisdiction scoping

For any state-scoped officer role (REV_OFF, REG_OFF, PLAN_OFF, TAX_OFF, STATE_ADMIN), a request targeting a parcel whose `state_code` differs from the officer's jurisdiction SHALL return HTTP 403 and SHALL NOT modify any database row.

**Validates: Requirements 5.4, 5.5**

### Property 7: Token blacklist prevents reuse

For any token that has been successfully submitted to `/auth/logout`, a subsequent request using that token SHALL return HTTP 401 and SHALL NOT proceed to any business logic.

**Validates: Requirements 4.3, 4.4**

### Property 8: Workflow event chain

For any `registration.completed` event published to Redis, the `workflow_tasks` table SHALL contain exactly one new row with `task_type = "MUTATION"` and `ulpin` matching the registration's ULPIN within the same transaction window.

**Validates: Requirements 9.1**
