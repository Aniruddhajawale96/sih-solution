# Workflows — Land Stack

## Workflow A — Citizen verifies ownership
1. Citizen opens Landing Page → clicks "Verify a Parcel".
2. Enters ULPIN (e.g. CH-UT-000001) on Ownership Verification screen.
3. Backend `GET /ror/{ulpin}` + `GET /parcels/{ulpin}` return masked Public schemas.
4. Citizen sees current owner (masked: "Ramesh K***"), tenure, mutation status, last updated.
5. Citizen downloads an Ownership Verification Certificate (PDF).
6. No audit log (read-only public action); no role escalation.

## Workflow B — Cross-department automated workflow (CORE DEMO)
This is the headline demo: a single deed registration cascades through departments automatically, visible live on the Sync Monitor.
1. REG_OFF logs in → Officer Dashboard → clicks "Register Deed".
2. Submits registration for CH-UT-000002 (Sale deed, Priya Sharma buys from Vikram Singh).
   - `POST /registration` writes registration row + audit_log(action=REGISTER_DEED).
   - Publishes `registration.completed` to Redis.
3. Workflow Engine consumes the event → creates a mutation task for REV_OFF.
   - Publishes `mutation.task_created`.
4. REV_OFF opens Mutation/Approval Workflow → sees task #12 → reviews deed + RoR.
   - Approves → `POST /workflow/12/approve` writes audit_log(action=APPROVE_MUTATION).
   - Publishes `mutation.approved`.
5. Workflow Engine consumes `mutation.approved` → triggers Tax Service reassessment.
   - `PUT /tax/{ulpin}` updates tax record → audit_log(action=REASSESS_TAX).
   - Publishes `tax.reassessed`.
6. Throughout steps 2–5, the Cross-Department Sync Monitor streams every event live.
7. Citizen opens Parcel 360 for CH-UT-000002 → instantly sees updated owner, Clear mutation status, reassessed tax.
8. End state: registration → mutation → tax, all chained, all audited, all live.

## Workflow C — AI/ML demo flow
1. PLAN_OFF opens Zoning & Violation Dashboard.
2. Uploads before/after satellite images for CH-UT-000002 → `POST /ml/change-detection`.
   - OpenCV diff → changed_area_sqm + estimated far_existing=3.1.
   - far_existing (3.1) > far_permitted (2.5) → `violation_flag=true`.
   - Zoning row updated + audit_log(action=ML_CHANGE_DETECTION).
3. CH-UT-000002 now shows a red [!] violation flag on the map + Parcel 360.
4. Separately: REG_OFF runs `POST /ml/fraud-score` on the CH-UT-000002 deed → fraud_score returned; if high, flagged for review.
5. Separately: REV_OFF uploads a legacy RoR scan → `POST /ml/ocr-extract` → extracted fields shown for review/confirm.

## Workflow D — Dev workflow (hackathon sprint plan, parallel agent tracks)
Two tracks run in parallel git worktrees (see docs/MULTI_AGENT_PARALLEL_WORKFLOW.md).
- **Hr 0**: Repo + worktrees initialized; frozen contracts set (openapi.yaml stub, DATA_SCHEMA.md, seed-data, RBAC_MATRIX.md).
- **Hr 0–2 Track A (backend)**: Database Agent sets up SQLAlchemy/GeoAlchemy2 models + Alembic + seed loaders; Security Agent builds auth + RBAC deps + audit.py; Backend Agent scaffolds routers (parcel, ror, registration, encumbrance, zoning, building_permission, tax).
- **Hr 0–2 Track B (frontend)**: DevOps Agent finalizes docker-compose + Nginx; Frontend Agent scaffolds Vite app + role routing + 16 screen shells; GIS Agent wires MapLibre + pg_tileserv.
- **Hr 2–4**: Track A adds workflow_engine (Redis pub/sub) + citizen services + admin + ML modules. Track B implements Parcel 360, Sync Monitor, Zoning Dashboard, Analytics.
- **Hr 4–5**: QA/Docs Agent runs pytest walkthroughs + manual screen tests; Orchestrator finalizes ROADMAP + SYNC_LOG.
- **Hr 5–6**: Final integration pass — `docker-compose up` from fresh clone; Standard Technical Document compiled; demo rehearsal per Workflow B.
Cadence: every ~1 hour, agents update docs/SYNC_LOG.md; Orchestrator resolves any contract drift.

## Workflow E — Git workflow
1. Trunk: `main`. Two long-lived worktrees: `track-a` (backend) and `track-b` (frontend), branched from `main`.
2. Each agent commits to its track branch with conventional messages: `feat(backend): add registration router`, `fix(frontend): mask owner_name on Parcel360`.
3. Contract files (openapi.yaml, DATA_SCHEMA.md, seed-data/*, RBAC_MATRIX.md) are frozen — changes require Orchestrator approval + SYNC_LOG entry, and must update both tracks.
4. A change affecting the other track (e.g. API shape change) MUST be logged in docs/SYNC_LOG.md and the other track notified before merge.
5. Integration PRs merge `track-a` and `track-b` into `main` only after the frozen contract still matches and `docker-compose up` is green.
6. Never force-push shared branches; never rewrite history after integration.
7. CI (GitHub Actions) runs on every PR: backend `pytest` + `ruff`, frontend `eslint` + `tsc`; PR cannot merge with failing checks.
