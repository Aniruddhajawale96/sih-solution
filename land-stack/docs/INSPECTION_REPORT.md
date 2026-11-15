# Track A Backend — Inspection Report

**Scope**: All files under `land-stack/backend/` plus seed data and docker-compose.  
**Reference contracts**: `docs/DATA_SCHEMA.md`, `docs/RBAC_MATRIX.md`, `docs/API_SPEC.md`, `AGENTS.md`.

---

## ✅ PASS

### Core architecture and patterns
- **FastAPI app structure** (`main.py`): lifespan context manager correctly starts and cancels the workflow consumer task. The `asynccontextmanager` / `AsyncGenerator` pattern is idiomatic for FastAPI 0.115.
- **Envelope schema** (`core/schemas.py`): `Envelope[T]`, `ErrorDetail`, `ok()`, and `err()` are correct Pydantic v2 `BaseModel` definitions. Generic typing via `TypeVar` is compatible with Pydantic v2's `model_dump()`.
- **Global exception handlers** (`main.py`): all three handlers (`StarletteHTTPException`, `RequestValidationError`, unhandled `Exception`) return `Envelope`-formatted JSON. The 422 handler correctly extracts the first validation error's field path and message.
- **Async database layer** (`core/database.py`): `create_async_engine`, `async_sessionmaker`, `AsyncSession` — all SQLAlchemy 2.0 async primitives used correctly. `expire_on_commit=False` is the right setting for async usage. `pool_pre_ping=True` is appropriate for a long-running server. `get_db` dependency correctly rolls back on exception and always closes the session.
- **Alembic async migration setup** (`alembic/env.py`): offline and online modes are both implemented. Online mode uses `async_engine_from_config` + `run_sync`, which is the canonical pattern for async Alembic. Engine is disposed after use.
- **Declarative base** (`core/database.py`): `DeclarativeBase` is the SQLAlchemy 2.0 style (not the legacy `declarative_base()`).
- **Mapped column typing** (all models): all models use `Mapped[T]` + `mapped_column(...)` — correct SQLAlchemy 2.0 ORM style throughout.
- **Parcel geometry** (`models/parcel.py`): `Geometry("POLYGON", srid=4326)` matches DATA_SCHEMA.md's requirement of GeoAlchemy2 with SRID 4326.
- **Nullable tehsil** (`models/parcel.py`): `tehsil: Mapped[str | None]` matches DATA_SCHEMA.md `nullable` annotation.
- **Audit log chain fields** (`models/audit_log.py`): `hash` and `prev_hash` are `String(64)` matching the SHA-256 hex-digest length. `default=datetime.utcnow` on `timestamp` is acceptable for a demo (see warning below).
- **ForeignKey relationships**: all Essential Layer models (`Ror`, `Registration`, `Encumbrance`, `Zoning`, `BuildingPermission`) correctly reference `parcels.ulpin`.
- **Registration `transaction_value`** (`models/registration.py`): correctly `Integer, nullable=False`. Comment references schema masking. Matches DATA_SCHEMA.md.
- **BuildingPermission `architect_ref`** (`models/building_permission.py`): correctly `nullable=True`. Matches DATA_SCHEMA.md note about older records.
- **Zoning `far_existing` default** (`models/zoning.py`): `default=0.0` is consistent with the schema. Comment notes that `violation_flag` invariant is enforced at the application layer, not DB — appropriate caveat.
- **Router stubs**: all 13 router files (`auth`, `parcel`, `ror`, `registration`, `encumbrance`, `zoning`, `building_permission`, `tax`, `workflow`, `citizen`, `admin`, `analytics`, `ml`) exist and expose a `router` attribute, so `main.py`'s `include_router` calls will not crash on import.
- **Workflow consumer stub** (`workflow_engine/consumer.py`): `start_consumer()` is a valid coroutine that returns immediately. `# pragma: no cover` is correctly applied to avoid test coverage noise for a stub.
- **requirements.txt**: all required libraries are pinned. `asyncpg` is notably absent as a direct dependency (see ERROR below), but all other packages are present.
- **Dockerfile**: multi-stage-free but correct — `libgdal-dev`, `libgeos-dev`, `libpq-dev` cover GeoAlchemy2 and psycopg2 native dependencies. `tesseract-ocr` covers pytesseract. Image is `python:3.11-slim`.
- **Seed data field names**: all seed JSON files (`ror.json`, `registration.json`, `encumbrance.json`, `zoning.json`, `building_permission.json`, `tax.json`) use the exact canonical field names from DATA_SCHEMA.md.
- **State adapter config** (`seed-data/state_adapter_config.json`): uses `canonical_field_name` values (`survey_or_khasra_no`, `owner_name`, `area_sqm`) that match DATA_SCHEMA.md. TN `area_acres → area_sqm` conversion factor `4046.86` is correct. No hardcoded state-specific logic in backend code — adapter pattern respected per Golden Rule 2.
- **ULPIN as universal join key**: ULPIN is the PK on `parcels`, PK+FK on `ror` and `zoning`, FK on `registration`, `encumbrance`, and `building_permission`. Consistent with Golden Rule 1.
- **Router prefix registration** (`main.py`): all 13 routers are registered under `/api/v1` with the correct path segments matching API_SPEC.md endpoints.
- **100% Python backend**: no Node.js or non-Python backend code present. Golden Rule 6 respected.
- **Envelope import in main.py**: `from core.schemas import err` — uses relative package import, which works when uvicorn is run from the `/app` directory (as in Dockerfile's `CMD`).

---

## ⚠️ WARNINGS

### W-01 — `datetime.utcnow` is deprecated in Python 3.12+
**File**: `backend/models/audit_log.py`, line 21  
**Issue**: `default=datetime.utcnow` (without `()`) is passed as a callable, which is correct SQLAlchemy usage, but `datetime.utcnow` itself is deprecated since Python 3.12. The Dockerfile uses `python:3.11-slim` so this won't fail today, but it will generate deprecation warnings if the base image is bumped to 3.12.  
**Fix**: Replace with `default=lambda: datetime.now(tz=timezone.utc)` and add `from datetime import timezone` to the import.

### W-02 — `models/__init__.py` exports only 3 of 7 models
**File**: `backend/models/__init__.py`  
**Issue**: Only `Parcel`, `User`, and `AuditLog` are imported. `Ror`, `Registration`, `Encumbrance`, `Zoning`, `BuildingPermission` (and the missing `Tax` model — see ERROR E-04) are not imported. `alembic/env.py` imports `from core.database import Base` and relies on model metadata being pre-registered, but only the 3 exported models will be included in autogenerate output. Alembic migrations will silently omit 4–5 tables.  
**Fix**: Import all models in `models/__init__.py`:
```python
from backend.models.ror import Ror
from backend.models.registration import Registration
from backend.models.encumbrance import Encumbrance
from backend.models.zoning import Zoning
from backend.models.building_permission import BuildingPermission
# from backend.models.tax import Tax  # once Tax model is created
```
Also update `__all__` accordingly.

### W-03 — `alembic/env.py` imports `Base` but not the model submodules
**File**: `backend/alembic/env.py`, line 29  
**Issue**: `from core.database import Base` imports `Base` but the comment says "Models are imported in `backend/models/__init__.py`". This is a fragile chain: Alembic autogenerate only sees tables whose models have been imported somewhere in the Python import chain before `Base.metadata` is inspected. Currently only 3 models are imported (W-02 above), so autogenerate will produce incomplete migrations.  
**Fix**: Add an explicit `import backend.models` (or `from backend import models`) in `env.py` after the `Base` import, or expand `models/__init__.py` as described in W-02. Either is acceptable; the explicit import in `env.py` is the more defensive approach.

### W-04 — Docker Compose `DATABASE_URL` driver mismatch
**File**: `land-stack/docker-compose.yml` (and `infra/docker-compose.yml`), `backend.environment.DATABASE_URL`  
**Issue**: The `backend` service sets `DATABASE_URL: postgresql+psycopg2://...`. The backend code (`core/database.py` and `alembic/env.py`) uses `create_async_engine` and `async_engine_from_config`, which require the `asyncpg` driver (`postgresql+asyncpg://`). Using `psycopg2` with an async engine will raise:  
```
sqlalchemy.exc.InvalidRequestError: The asyncio extension requires an async driver to be used.
```  
**Fix**: Change the `DATABASE_URL` in both `docker-compose.yml` files to `postgresql+asyncpg://landstack:landstack@postgres:5432/landstack`.

### W-05 — `asyncpg` missing from `requirements.txt`
**File**: `backend/requirements.txt`  
**Issue**: `asyncpg` is the runtime driver required by `create_async_engine` with `postgresql+asyncpg://`. It is not listed in `requirements.txt`. The service will fail to start in the container.  
**Fix**: Add `asyncpg==0.29.0` (or the latest compatible version) to `requirements.txt`.

### W-06 — `users.json` stores plaintext passwords
**File**: `seed-data/users.json`  
**Issue**: All demo users have `"password": "demo123"` in plaintext. The `User` model stores `hashed_password`, meaning any seed loader will need to hash these before inserting. If a seed loader naively inserts the JSON verbatim (a likely mistake), authentication will silently fail or the app will crash on the bcrypt compare.  
**Fix**: Either pre-hash the passwords in the JSON using bcrypt (`passlib.hash.bcrypt.hash("demo123")`) and rename the field to `hashed_password`, or add a note in the seed loader that passwords must be hashed before insert. The JSON field name `password` does not match the model's `hashed_password` column, which will cause any ORM-based bulk-insert to fail with a column mapping error.

### W-07 — `violation_flag` invariant has no DB enforcement
**File**: `backend/models/zoning.py`, docstring  
**Issue**: The docstring explicitly notes that `violation_flag` is maintained at the application layer. However, there is no DB check constraint to prevent `far_existing > far_permitted` with `violation_flag = False` (or vice versa), meaning a direct DB write or a future code path that skips the application logic will silently corrupt the flag.  
**Fix**: Add a `CheckConstraint` to the `Zoning` model (or as a migration) that enforces the invariant at the DB level:  
```python
from sqlalchemy import CheckConstraint
__table_args__ = (
    CheckConstraint(
        "(far_existing <= far_permitted) OR (violation_flag = TRUE)",
        name="ck_zoning_violation_flag_consistent",
    ),
)
```

### W-08 — Seed data `users.json` missing `state_admin_chd` for Chandigarh
**File**: `seed-data/users.json`  
**Issue**: There is a `state_admin_tn` for Tamil Nadu but no `STATE_ADMIN` for Chandigarh. The demo scenario includes Chandigarh-scoped officers but the cross-department override role for CH is absent. This won't cause a crash but will make demo scenarios involving STATE_ADMIN approvals for CH fail silently with a 403.  
**Fix**: Add `{"username": "state_admin_chd", "password": "demo123", "role": "STATE_ADMIN", "jurisdiction": "CH"}` to `users.json`.

### W-09 — `seed-data/` mounted as PostgreSQL init scripts will not load JSON
**File**: `land-stack/docker-compose.yml` (and `infra/docker-compose.yml`), `postgres.volumes`  
**Issue**: `../seed-data:/docker-entrypoint-initdb.d` mounts the seed directory as PostgreSQL init scripts. PostgreSQL's `docker-entrypoint-initdb.d` only auto-executes `.sql` and `.sh` files; it ignores `.json` and `.geojson` files. The seed data will not be loaded automatically.  
**Fix**: Add a `seed.sh` script (or a SQL COPY command for each JSON file) in the seed-data directory, or add a separate `seed` service in docker-compose that runs after `postgres` is healthy and uses a Python/psql loader script.

### W-10 — `alembic.ini` `sqlalchemy.url` placeholder uses environment variable interpolation syntax that may not work
**File**: `backend/alembic.ini`, `sqlalchemy.url = %(DATABASE_URL)s`  
**Issue**: Alembic's `%(VAR)s` interpolation reads from the `[alembic]` INI section, not from OS environment variables. The value `%(DATABASE_URL)s` will only resolve if `DATABASE_URL` is explicitly set in the INI. Since `alembic/env.py` overrides `sqlalchemy.url` via `config.set_main_option(...)`, this is safe at runtime — but running `alembic` directly from the CLI without the `env.py` override (e.g., in a migration dry-run) will produce a `KeyError: DATABASE_URL` from ConfigParser.  
**Fix**: Replace `%(DATABASE_URL)s` with a safe placeholder like `driver://user:pass@localhost/db` (a dummy value that is always overridden by `env.py`). Add a comment noting that `env.py` sets the real URL at runtime.

### W-11 — `JWT_SECRET` hardcoded as `devsecret` in both Compose files
**File**: `land-stack/docker-compose.yml` and `infra/docker-compose.yml`, `backend.environment.JWT_SECRET`  
**Issue**: `JWT_SECRET: devsecret` is committed to source control in both Compose files. This is acceptable for a local dev/demo environment, but should be blocked from production. Any signing key committed to source control should be treated as compromised.  
**Fix**: Move to a `.env` file (gitignored) or Docker secrets for production deployment. Add a `.env.example` file with `JWT_SECRET=CHANGE_ME` and document the requirement in `docs/ARCHITECTURE.md`.

### W-12 — `land-stack/docker-compose.yml` and `infra/docker-compose.yml` are identical duplicates
**File**: both files  
**Issue**: Both files are byte-for-byte identical. Having two canonical compose files will cause divergence over time.  
**Fix**: Delete one and reference the other, or make `land-stack/docker-compose.yml` a thin wrapper that extends `infra/docker-compose.yml` via `extends`.

### W-13 — No `Tax` model referenced in `models/__init__.py` or seed loader
**File**: `backend/models/__init__.py` and `seed-data/tax.json`  
**Issue**: `tax.json` has 3 records but there is no `Tax` SQLAlchemy model file (see ERROR E-04). `models/__init__.py` does not import any `Tax` class. The tax router is registered in `main.py` but the backing model and table do not exist.

---

## ❌ ERRORS

### E-01 — `main.py` import path uses bare `core.schemas` but container WORKDIR is `/app`
**File**: `backend/main.py`, lines 17–18 and all router imports  
**What's wrong**: `main.py` uses bare (non-package-relative) imports: `from core.schemas import err`, `from routers import auth as auth_router`, etc. This works when uvicorn is launched from `/app` with the working directory on `sys.path`. The Dockerfile `CMD` does `uvicorn main:app --host 0.0.0.0 --port 8000` from `WORKDIR /app` — this is fine.

However, all SQLAlchemy **model** files use package-qualified imports: `from backend.core.database import Base`. This is inconsistent. If `main.py` is the entry point and `/app` is on `sys.path`, then `backend` is a sub-package of `/app`, but there is no `/app/backend/__init__.py` making `backend` a package — the `backend/` directory itself is the app root. This means:
- `from backend.core.database import Base` in model files will raise `ModuleNotFoundError: No module named 'backend'` at import time inside the container.
- `from core.database import Base` (as used in `main.py` and `alembic/env.py`) would work correctly.

**Fix**: Standardize all imports to the bare form (`from core.database import Base`, `from models.parcel import Parcel`, etc.). The `backend/` directory is the package root (`WORKDIR /app`, `COPY . .` puts files directly under `/app`), so `backend.X` will not resolve. Affected files: `models/audit_log.py`, `models/parcel.py`, `models/users.py`, `models/ror.py`, `models/registration.py`, `models/encumbrance.py`, `models/zoning.py`, `models/building_permission.py` — all import `from backend.core.database import Base`. Each must become `from core.database import Base`.

### E-02 — `models/__init__.py` also uses `backend.*` import paths (crash on import)
**File**: `backend/models/__init__.py`, lines 4–6  
**What's wrong**: 
```python
from backend.models.audit_log import AuditLog
from backend.models.parcel import Parcel
from backend.models.users import User
```
Same `backend.*` namespace issue as E-01. `alembic/env.py` does `from core.database import Base` (bare form, correct), then relies on model metadata being registered — but `models/__init__.py` will crash before any models register because the `backend.*` paths don't resolve.  
**Fix**: Change to:
```python
from models.audit_log import AuditLog
from models.parcel import Parcel
from models.users import User
```

### E-03 — `asyncpg` driver not installed + wrong driver in `DATABASE_URL` = service crash on startup
**Files**: `backend/requirements.txt`, `land-stack/docker-compose.yml`  
**What's wrong**: This is the combination of W-04 and W-05 as a hard failure:
1. `requirements.txt` does not include `asyncpg`.
2. `docker-compose.yml` sets `DATABASE_URL=postgresql+psycopg2://...`.

When the container starts, `create_async_engine("postgresql+psycopg2://...")` will raise `sqlalchemy.exc.InvalidRequestError` because psycopg2 is a synchronous driver and cannot back an async engine. Even if the URL were corrected to `asyncpg`, the import of `asyncpg` would fail at the driver-loading step because the package is not installed.  
**Fix**:  
1. Add `asyncpg==0.29.0` to `requirements.txt`.  
2. Change both `docker-compose.yml` files' `DATABASE_URL` to `postgresql+asyncpg://landstack:landstack@postgres:5432/landstack`.

### E-04 — `Tax` model does not exist; `tax` router and `main.py` will crash
**Files**: `backend/models/` (no `tax.py`), `backend/routers/tax.py`, `backend/main.py` line for tax router  
**What's wrong**: `DATA_SCHEMA.md` defines a `tax` table with fields `ulpin`, `assessment_id`, `annual_tax`, `last_paid_date`, `payment_status`, `arrears`. No `backend/models/tax.py` file exists. `main.py` imports and registers `tax_router`, which currently imports cleanly as a stub — but the moment the tax router is implemented and needs `from models.tax import Tax`, it will crash with `ModuleNotFoundError`. Alembic autogenerate will never produce the `tax` table migration. `seed-data/tax.json` has valid data that cannot be loaded.  
**Fix**: Create `backend/models/tax.py`:
```python
from datetime import date
from sqlalchemy import Date, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from core.database import Base

class Tax(Base):
    __tablename__ = "tax"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ulpin: Mapped[str] = mapped_column(String, ForeignKey("parcels.ulpin"), nullable=False)
    assessment_id: Mapped[str] = mapped_column(String, nullable=False)
    annual_tax: Mapped[int] = mapped_column(Integer, nullable=False)
    last_paid_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    payment_status: Mapped[str] = mapped_column(String, nullable=False)
    arrears: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
```
Then add `from models.tax import Tax` to `models/__init__.py`.  
**Note**: DATA_SCHEMA.md shows `tax` as a 1:1 with `parcel` (like `ror` and `zoning`), so `ulpin` could be the PK directly. Use an `id` PK if multiple assessments per parcel are anticipated, or `ulpin` as PK if strictly 1:1. Clarify with the schema owner — the current schema doc says `(1) ---- (0..1) tax`.

### E-05 — `StateAdapterConfig` model does not exist; `admin` router has no backing model
**Files**: `backend/models/` (no `state_adapter_config.py`), `backend/routers/admin.py`  
**What's wrong**: DATA_SCHEMA.md defines a `state_adapter_config` table. API_SPEC.md defines `GET /admin/state-adapter/{state_code}` and `PUT /admin/state-adapter/{state_code}`. No model file exists. The admin router is a stub today, but once implemented will immediately fail without this model. Alembic will never create the table.  
**Fix**: Create `backend/models/state_adapter_config.py`:
```python
from sqlalchemy import Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from core.database import Base

class StateAdapterConfig(Base):
    __tablename__ = "state_adapter_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    state_code: Mapped[str] = mapped_column(String, nullable=False)
    source_field_name: Mapped[str] = mapped_column(String, nullable=False)
    canonical_field_name: Mapped[str] = mapped_column(String, nullable=False)
    unit_conversion_factor: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    language_code: Mapped[str] = mapped_column(String, nullable=False)
```
Add to `models/__init__.py`. Add a `UniqueConstraint` on `(state_code, source_field_name)` to prevent duplicate mappings.

### E-06 — No `WorkflowTask` model; workflow router cannot be implemented
**Files**: `backend/models/` (no `workflow_task.py`), `backend/routers/workflow.py`  
**What's wrong**: API_SPEC.md defines `GET /workflow/tasks`, `POST /workflow/{taskId}/approve`, and `POST /workflow/{taskId}/reject`. These require a `workflow_tasks` table. No model exists. The consumer stub in `workflow_engine/consumer.py` says task 10.1 will add the real loop — but that loop needs a table to write tasks to.  
**Fix**: Create `backend/models/workflow_task.py`. Minimum fields per the API spec: `id` (PK), `ulpin` (FK → parcels), `task_type` (string: MUTATION/ZONING/TAX), `assigned_role` (string), `status` (PENDING/APPROVED/REJECTED), `created_at` (datetime), `comment` (nullable string). Add to `models/__init__.py`.

### E-07 — No `CitizenServiceRequest` model; citizen router cannot be implemented
**Files**: `backend/models/` (no `citizen_service_request.py`), `backend/routers/citizen.py`  
**What's wrong**: API_SPEC.md defines `POST /citizen/service-request` and `GET /citizen/requests`. These require a backing table. No model exists.  
**Fix**: Create `backend/models/citizen_service_request.py`. Minimum fields: `id` (auto PK or UUID), `ulpin` (FK → parcels), `username` (FK → users), `service_type` (string), `notes` (nullable string), `status` (string), `created_at` (datetime). Add to `models/__init__.py`.

### E-08 — Alembic `env.py` imports `from core.database import Base` but no model files are imported; autogenerate produces empty migrations
**File**: `backend/alembic/env.py`, line 29  
**What's wrong**: The comment says models are imported via `backend/models/__init__.py`, but `env.py` never actually imports that module. The line `from core.database import Base` only imports the `Base` class — it does not trigger the import of any model submodule. `Base.metadata` will contain zero tables when autogenerate runs, producing a migration that drops all tables (or creates none).  
**Fix**: Add after line 29:
```python
import models  # noqa: F401 — registers all ORM models with Base.metadata
```
This relies on `models/__init__.py` importing all models (W-02 fix above).

### E-09 — `psycopg2-binary` in `requirements.txt` conflicts with async-only usage
**File**: `backend/requirements.txt`  
**What's wrong**: `psycopg2-binary==2.9.9` is listed but is not needed for async operation (which uses `asyncpg`). It is also incompatible as the driver for `create_async_engine`. Its presence does not cause a crash on its own, but keeping it creates confusion and may be pulled in as the wrong driver if any code path uses `create_engine` (synchronous) instead of `create_async_engine`.  
**Fix**: Remove `psycopg2-binary` from `requirements.txt`. The only DB driver needed is `asyncpg`. If synchronous queries are ever needed (e.g., shell scripts), use `psycopg2-binary` only in a separate dev-tools requirements file.

---

## Summary Table

| ID | Severity | File(s) | Short description |
|---|---|---|---|
| E-01 | ERROR | All model files | `from backend.core.database import Base` will `ModuleNotFoundError` in container |
| E-02 | ERROR | `models/__init__.py` | `from backend.models.*` imports crash before any model registers with Base |
| E-03 | ERROR | `requirements.txt`, both `docker-compose.yml` | Missing `asyncpg`; wrong sync driver in `DATABASE_URL`; service crashes on start |
| E-04 | ERROR | (missing) `models/tax.py` | `Tax` model and table do not exist; `tax.json` seed data unloadable |
| E-05 | ERROR | (missing) `models/state_adapter_config.py` | `StateAdapterConfig` model missing; admin router unimplementable |
| E-06 | ERROR | (missing) `models/workflow_task.py` | `WorkflowTask` model missing; workflow router unimplementable |
| E-07 | ERROR | (missing) `models/citizen_service_request.py` | `CitizenServiceRequest` model missing; citizen router unimplementable |
| E-08 | ERROR | `alembic/env.py` | Models never imported into env; autogenerate produces empty/destructive migrations |
| E-09 | ERROR | `requirements.txt` | `psycopg2-binary` is the wrong driver for async engine; conflicts with asyncpg |
| W-01 | WARNING | `models/audit_log.py` | `datetime.utcnow` deprecated; will warn on Python 3.12+ |
| W-02 | WARNING | `models/__init__.py` | Only 3 of 7+ models exported; Alembic misses tables |
| W-03 | WARNING | `alembic/env.py` | Fragile model import chain; models not guaranteed to be loaded |
| W-04 | WARNING | both `docker-compose.yml` | `postgresql+psycopg2` driver in `DATABASE_URL` incompatible with async engine |
| W-05 | WARNING | `requirements.txt` | `asyncpg` missing (covered also in E-03) |
| W-06 | WARNING | `seed-data/users.json` | Plaintext passwords; field name `password` ≠ model column `hashed_password` |
| W-07 | WARNING | `models/zoning.py` | `violation_flag` has no DB-level `CheckConstraint`; can silently drift |
| W-08 | WARNING | `seed-data/users.json` | No `STATE_ADMIN` for Chandigarh; CH admin demo scenarios will 403 |
| W-09 | WARNING | both `docker-compose.yml` | JSON/GeoJSON seed files not auto-loaded by postgres init-scripts mechanism |
| W-10 | WARNING | `backend/alembic.ini` | `%(DATABASE_URL)s` INI interpolation fails without env override; misleading placeholder |
| W-11 | WARNING | both `docker-compose.yml` | `JWT_SECRET: devsecret` hardcoded in source control |
| W-12 | WARNING | both `docker-compose.yml` | Duplicate identical files; will diverge |
| W-13 | WARNING | `models/__init__.py` | `Tax` model missing (duplicates E-04 from structural angle) |

---

## Priority Fix Order

1. **E-01 + E-02** — Fix all `backend.core.*` / `backend.models.*` import paths to bare form. This is a single global find-and-replace; nothing runs until this is done.
2. **E-03 + E-04 (W-04, W-05, E-09)** — Add `asyncpg` to requirements, remove `psycopg2-binary`, fix both Compose `DATABASE_URL` values to `asyncpg` driver.
3. **E-04** — Create `models/tax.py`.
4. **E-05, E-06, E-07** — Create `models/state_adapter_config.py`, `models/workflow_task.py`, `models/citizen_service_request.py`.
5. **E-08 + W-02** — Expand `models/__init__.py` to import all models; add `import models` to `alembic/env.py`.
6. **W-06** — Fix `users.json` to use `hashed_password` with pre-hashed values (or add loader script).
7. **W-09** — Add a seed loader script so JSON data is actually inserted on `docker compose up`.
8. All remaining warnings in any order.
