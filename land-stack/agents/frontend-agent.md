# Frontend Agent (Track B)
Owns: all screens in docs/SCREENS.md and docs/WIREFRAMES.md.
Tech: React + Vite + TypeScript, TailwindCSS + shadcn/ui, MapLibre GL JS, Zustand, TanStack Query, Recharts.

Must implement:
- Role-based routing for all 7 roles defined in docs/RBAC_MATRIX.md
- The Cross-Department Sync Monitor as a real-time (polling/SSE) log view
- Field-level masking display logic matching docs/RBAC_MATRIX.md's masking table

Treats /backend/openapi.yaml and docs/DATA_SCHEMA.md as read-only contracts.
