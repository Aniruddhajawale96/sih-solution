# Implementation Plan: Frontend–Backend Integration (Remaining Screen Fixes)

## Overview

Fix API endpoint mismatches in the remaining frontend screens so every call matches the actual FastAPI backend routes documented in docs/API_SPEC.md. Remove any UI features that call non-existent endpoints.

## Tasks

- [x] 1. Fix remaining frontend screen API endpoints
  - [ ] 1.1 Fix StateAdminPanel.tsx
    - Replace `/admin/state/analytics` with `GET /analytics/state/{jurisdiction}`
    - Replace `/admin/state/users` with `GET /admin/users`
    - Replace `/admin/state/adapters` with `GET /admin/state-adapter/{jurisdiction}`
    - Remove the user active-toggle control (no backing endpoint)
    - Remove the adapter sync control (no backing endpoint)
    - _Requirements: backend routes must match API_SPEC.md; RBAC roles state_admin_
  - [ ] 1.2 Fix WorkflowApproval.tsx
    - Replace direct `GET /workflow/tasks/{id}` with `GET /workflow/tasks` (list) then find the task by id client-side
    - Replace `/workflow/tasks/{id}/approve` with `POST /workflow/{id}/approve`
    - Replace `/workflow/tasks/{id}/reject` with `POST /workflow/{id}/reject`
    - Change reject request body key from `comment` to `reason`
    - _Requirements: approve/reject actions must produce an audit_log entry; RBAC roles land_officer, registrar_
  - [ ] 1.3 Fix ZoningDashboard.tsx
    - Remove the `GET /zoning/violations` call (endpoint does not exist)
    - Add a ULPIN input field; look up zoning data via `GET /zoning/{ulpin}`
    - Retain the existing `POST /ml/change-detection` multipart upload unchanged
    - _Requirements: ULPIN is the universal join key; zoning data served per-parcel_
  - [ ] 1.4 Verify OfficerDashboard.tsx
    - Confirm the component calls `GET /workflow/tasks` (list endpoint) and not a non-existent single-task endpoint
    - Fix any mismatch found; no change needed if already correct
    - _Requirements: land_officer role sees only tasks in own jurisdiction_
  - [ ] 1.5 Build check
    - Run `cd frontend && npm run build` and resolve all TypeScript and Vite build errors introduced by the above changes
    - _Requirements: frontend must compile cleanly before commit_
  - [ ] 1.6 Commit
    - Stage all changed files and commit with message: `fix(integration): fix remaining screen API endpoints`
    - _Requirements: docs/SYNC_LOG.md updated if any API shape changed_

## Notes

- Tasks marked with `*` are optional and can be skipped for a faster MVP (none in this plan — all tasks are required).
- Each task references specific backend routes; check `docs/API_SPEC.md` for authoritative signatures before editing.
- RBAC enforcement remains server-side; the frontend should only hide controls whose backing endpoint does not exist — it must not invent its own role checks.
- Do not introduce Node.js/Express backend logic; backend is 100% FastAPI (Python).

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2", "1.3", "1.4"] },
    { "id": 1, "tasks": ["1.5"] },
    { "id": 2, "tasks": ["1.6"] }
  ]
}
```
