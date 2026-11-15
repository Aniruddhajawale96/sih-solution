# Tech Stack — Land Stack

## Frontend (Track B)
| Layer | Technology | Version | Purpose |
|---|---|---|---|
| Framework | React | 18.x | Component UI runtime |
| Build tool | Vite | 5.x | Dev server + bundler |
| Language | TypeScript | 5.x | Type safety, matches DATA_SCHEMA.md / openapi.yaml codegen |
| Styling | TailwindCSS | 3.x | Utility-first CSS |
| Component library | shadcn/ui | latest | Accessible primitives (built on Radix) |
| Maps | MapLibre GL JS | 4.x | Open-source vector-tile WebGL map renderer |
| State | Zustand | 4.x | Lightweight global store (auth/role state) |
| Server state | TanStack Query | 5.x | Data fetching, caching, polling for Sync Monitor |
| Charts | Recharts | 2.x | Analytics dashboards (national/state) |
| Routing | React Router | 6.x | Role-based route guards |

Frontend reads `/backend/openapi.yaml` as a read-only contract; API client types are generated, never hand-written.

## Backend (Track A — 100% Python)
| Layer | Technology | Version | Purpose |
|---|---|---|---|
| Web framework | FastAPI | 0.115.0 | Async routers, auto OpenAPI |
| ASGI server | Uvicorn[standard] | 0.30.6 | Dev + prod server |
| ORM | SQLAlchemy | 2.0.35 | Declarative models, ULPIN as join key |
| GIS ORM | GeoAlchemy2 | 0.15.2 | PostGIS Geometry columns, SRID 4326 |
| DB driver | psycopg2-binary | 2.9.9 | PostgreSQL driver |
| Migrations | Alembic | 1.13.3 | Schema versioning |
| Validation | Pydantic | 2.9.2 | Public vs Internal response schemas (masking) |
| Auth | python-jose[cryptography] | 3.3.0 | JWT encode/decode (access + refresh) |
| Password hashing | passlib[bcrypt] | 1.7.4 | User credential hashing |
| Cache/pub-sub | redis | 5.0.8 | Event bus for cross-department workflow |
| Multipart | python-multipart | 0.0.9 | File uploads (deeds, satellite images) |
| Object storage | boto3 | 1.35.36 | MinIO S3-compatible client |
| Testing | pytest | 8.3.3 | Backend unit + integration tests |
| HTTP test client | httpx | 0.27.2 | FastAPI TestClient transport |

The backend is strictly Python; no Node.js/Express is permitted for backend logic (see AGENTS.md rule 6).

## AI / ML (Track A — same Python runtime as backend)
| Library | Version | Purpose |
|---|---|---|
| opencv-python-headless | 4.10.0.84 | Satellite before/after change detection, FAR estimation |
| scikit-learn | 1.5.2 | Isolation Forest fraud/anomaly scoring on transactions |
| pytesseract | 0.3.13 | OCR of legacy RoR scans + regex field extraction |

ML modules live under `/backend/ml/*` and run in-process with FastAPI. For prototype speed, rule-based/simplified models are acceptable. Exposed via `/api/v1/ml/*`.

## Database / GIS
| Component | Version | Purpose |
|---|---|---|
| PostgreSQL | 16 | Primary relational store; every table joins on `ulpin` |
| PostGIS | 3.4 | Spatial indexing, geometry storage, SRID 4326 |
| pg_tileserv | latest | Serves parcel vector tiles to MapLibre (MVT) |
| MinIO | latest | S3-compatible object store for deed scans, encumbrance certs, satellite images |

## Security
- JWT (access + refresh) issued by FastAPI; access short-lived, refresh longer-lived.
- RBAC enforced via FastAPI dependency injection on every route (docs/RBAC_MATRIX.md).
- Hash-chained audit log: each row's `hash` = SHA-256(prev_hash + row contents); tamper-evident.
- Field-level masking via distinct Pydantic Public vs Internal schemas.
- Nginx reverse proxy terminates TLS in production and fronts both frontend (3000) and backend (8000).

## DevOps
| Component | Purpose |
|---|---|
| Docker Compose | Prototype orchestration: postgres, pg_tileserv, redis, minio, backend, frontend — one `docker-compose up` |
| GitHub Actions | CI on PR: backend `pytest` + `ruff` lint; frontend `eslint` + `tsc` typecheck |
| Nginx | Reverse proxy, static frontend serving, API gateway to FastAPI |

## Production Path (post-hackathon)
- Replace Docker Compose with Kubernetes (Postgres via CloudNativePG, MinIO operator, FastAPI Deployment with HPA).
- Add Redis Sentinel/Cluster for the event bus; pg_tileserv scaled horizontally behind a load balancer.
- Move ML inference behind a Celery worker pool or a Triton/ONNX runtime; keep FastAPI route as the orchestrator.
- Centralized secrets via Vault; JWT signing keys rotated; audit log mirrored to an append-only WORM store (S3 Object Lock).
- Observability: OpenTelemetry traces from frontend → Nginx → FastAPI → Postgres; Prometheus metrics; Loki/Grafana logs.
- Multi-state rollout: each state onboarded by adding a `state_adapter_config` entry — no code changes (State Adapter pattern pays off).
- Interop: expose the same REST/OpenAPI contract as a data exchange gateway for other states' existing systems; converge toward NDEAR-style land records interoperability standards.
