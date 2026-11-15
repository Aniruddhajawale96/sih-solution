# Wireframes — Land Stack (16 Screens)

ASCII wireframes with named components (PascalCase). Each screen lists its components. See docs/SCREENS.md for routes/roles.

---

## Screen 1 — Landing Page
```
+--------------------------------------------------------------+
| TopNav:  [LandStack logo]   [Map] [Verify]  [Login v]         |
+--------------------------------------------------------------+
|                                                              |
|   HeroSection                                                |
|   "Unified Land Governance, anchored by ULPIN"               |
|   [Verify a Parcel ->]   [Explore Map]                        |
|                                                              |
+--------------------------------------------------------------+
| FeatureStrip: [3-Layer GIS] [State Adapter] [AI/ML] [Audit]  |
+--------------------------------------------------------------+
| PilotCards:  [Chandigarh Urban]    [Tamil Nadu Rural]         |
+--------------------------------------------------------------+
| Footer:  links | SIH PS #26014 | DoLR                         |
+--------------------------------------------------------------+
```
Components: TopNav, HeroSection, FeatureStrip, PilotCards, Footer

---

## Screen 2 — GIS Map Explorer
```
+--------------------------------------------------------------+
| TopNav:  [LandStack]  [Map] [Verify] [Login]                  |
+------------+-----------------------------------+-------------+
| LayerPanel | MapCanvas (MapLibre)              | ParcelPreview|
| [x] Base   |                                   | ULPIN: ...   |
| [ ] Essen.. |   [cadastral polygons]            | Area: ...    |
| [ ] Addon  |   [pan/zoom controls]             | [Open 360 ->]|
| [ ] Violat.|                                   |              |
| StateFilter|                                   |              |
| [x] CH     |                                   |              |
| [x] TN     |                                   |              |
+------------+-----------------------------------+-------------+
| SearchBar: [ULPIN / Khasra / Survey No.   ] [Search]         |
+--------------------------------------------------------------+
```
Components: TopNav, LayerPanel (BaseToggle, EssentialToggle, AdditionalToggle, ViolationToggle, StateFilter), MapCanvas (MapLibre), ParcelPreview, SearchBar

---

## Screen 3 — Parcel 360 View
```
+--------------------------------------------------------------+
| TopNav:  [< Back]  ULPIN: CH-UT-000002          [Print] [Share]|
+--------------------------------------------------------------+
| ParcelHeader:  Sector 17, Chandigarh | 380.2 sqm | Commercial|
+-----------------------+--------------------------------------+
| TabBar: [Base] [RoR] [Registration] [Encumbrance] [Zoning] [Tax]|
+-----------------------+--------------------------------------+
| LayerCard (selected tab content)                             |
|   OwnerCard: Priya S*** (masked for citizen)                 |
|   TenureBadge: Freehold   MutationStatus: Clear               |
|   ...                                                         |
+-----------------------+--------------------------------------+
| EncumbranceCard: Mortgage - State Bank of India (Active)      |
| ZoningCard: Commercial | FAR 3.1 / 2.5 | ViolationFlag [!]    |
| TaxCard: Arrears Rs.28,000 (Overdue)  [public]                |
+--------------------------------------------------------------+
| MiniMap: parcel polygon highlighted                           |
+--------------------------------------------------------------+
```
Components: TopNav, ParcelHeader, TabBar, OwnerCard, TenureBadge, MutationStatus, EncumbranceCard, ZoningCard, ViolationFlag, TaxCard, MiniMap

---

## Screen 4 — Ownership Verification
```
+--------------------------------------------------------------+
| TopNav:  [< Back]  Verify Ownership — CH-UT-000001             |
+--------------------------------------------------------------+
| VerifyForm: [ULPIN ____________] [Verify]                     |
+--------------------------------------------------------------+
| OwnerVerificationResult                                       |
|   Current Owner: Ramesh K*** (masked)                         |
|   TenureType: Freehold                                         |
|   KhatauniNo: KH-0021                                         |
|   MutationStatus: Clear                                        |
|   LastUpdated: 2026-09-10                                     |
+--------------------------------------------------------------+
| VerificationCertificate [Download PDF]                        |
+--------------------------------------------------------------+
```
Components: TopNav, VerifyForm, OwnerVerificationResult, VerificationCertificate

---

## Screen 5 — Service Request Portal
```
+--------------------------------------------------------------+
| TopNav:  [Citizen: citizen_demo]  [Dashboard] [Logout]        |
+--------------------------------------------------------------+
| ServiceRequestForm                                            |
|   ULPIN: [_______________]                                    |
|   ServiceType: [Ownership Cert v] / [Mutation] / [Encumbrance]|
|   Notes: [_________________]                                  |
|   [Submit Request]                                            |
+--------------------------------------------------------------+
| MyRecentRequests: list of submitted requests w/ status        |
+--------------------------------------------------------------+
```
Components: TopNav, ServiceRequestForm, MyRecentRequests

---

## Screen 6 — Request Tracking
```
+--------------------------------------------------------------+
| TopNav:  [Citizen: citizen_demo]  [Dashboard] [Logout]        |
+--------------------------------------------------------------+
| RequestFilter: [All v] [Pending] [Fulfilled] [Rejected]      |
+--------------------------------------------------------------+
| RequestList                                                   |
|  REQ-1001 | Ownership Cert | CH-UT-000001 | Fulfilled         |
|  REQ-1002 | Mutation        | CH-UT-000003 | Pending          |
+--------------------------------------------------------------+
| RequestDetail (on select): status timeline + officer comment  |
+--------------------------------------------------------------+
```
Components: TopNav, RequestFilter, RequestList, RequestDetail

---

## Screen 7 — Citizen Login / Dashboard
```
+--------------------------------------------------------------+
| LoginCard                                                     |
|   [username] [password] [Login]                              |
+--------------------------------------------------------------+
| (after login) CitizenDashboard                               |
|   OwnedParcels: [CH-UT-000001] [TN-TJ-000004]                 |
|   OpenRequests: 2   FulfilledRequests: 5                     |
|   QuickActions: [New Service Request] [Verify Parcel]         |
+--------------------------------------------------------------+
```
Components: LoginCard, CitizenDashboard, OwnedParcels, QuickActions

---

## Screen 8 — Officer Login
```
+--------------------------------------------------------------+
| OfficerLoginCard                                              |
|   [username] [password] [Login]                              |
|   Role auto-detected -> redirect to OfficerDashboard         |
+--------------------------------------------------------------+
```
Components: OfficerLoginCard

---

## Screen 9 — Officer Dashboard
```
+--------------------------------------------------------------+
| TopNav:  [Officer: reg_officer_chd]  [Sync] [Logout]          |
+--------------------------------------------------------------+
| DashboardHeader: Registration Officer — Chandigarh           |
+-------------------+-------------------+----------------------+
| PendingTasksCard  | RecentActivity     | QuickActionsCard    |
|  Mutation: 3      |  deed registered   | [Register Deed]    |
|  Zoning: 1        |  mutation approved | [Run Fraud Score]   |
|  Tax: 2           |  ...               | [Sync Monitor]      |
+-------------------+-------------------+----------------------+
```
Components: TopNav, DashboardHeader, PendingTasksCard, RecentActivity, QuickActionsCard

---

## Screen 10 — Mutation / Approval Workflow
```
+--------------------------------------------------------------+
| TopNav:  [Officer: rev_officer_chd]  [Dashboard] [Logout]     |
+--------------------------------------------------------------+
| TaskQueueFilter: [All v] [Mutation] [Zoning] [Tax]  [Pending]|
+--------------------------------------------------------------+
| TaskList                                                       |
|  #12 Mutation | CH-UT-000003 | Anil Mehta | [Approve][Reject]|
|  #13 Zoning   | CH-UT-000002 | FAR 3.1>2.5 | [Approve][Reject]|
+--------------------------------------------------------------+
| TaskDetail (on select):                                        |
|   ParcelSummary | DeedSummary | ApprovalForm (comment) [Approve]|
|   (writes audit_log, publishes next event)                    |
+--------------------------------------------------------------+
```
Components: TopNav, TaskQueueFilter, TaskList, TaskDetail, ParcelSummary, DeedSummary, ApprovalForm

---

## Screen 11 — Zoning & Violation Dashboard
```
+--------------------------------------------------------------+
| TopNav:  [Officer: plan_officer_chd]  [Dashboard] [Logout]    |
+--------------------------+-----------------------------------+
| ViolationMap (MapLibre)   | ViolationTable                    |
|   parcels colored by      |  ULPIN | FAR | Permitted | Flag   |
|   violation_flag          |  CH-UT-000002 | 3.1 | 2.5 | [!]  |
|                          |                                   |
+--------------------------+-----------------------------------+
| ChangeDetectionPanel: [Upload before] [Upload after] [Run]  |
|   Result: changed_area_sqm=... far_existing_est=... [Save]   |
+--------------------------------------------------------------+
```
Components: TopNav, ViolationMap, ViolationTable, ChangeDetectionPanel

---

## Screen 12 — Cross-Department Sync Monitor
```
+--------------------------------------------------------------+
| TopNav:  [Officer]  [Dashboard] [Logout]                     |
+--------------------------------------------------------------+
| SyncFeed (SSE / polling, live)                                |
|  14:02 registration.completed | CH-UT-000002 | reg_officer_chd|
|  14:02 mutation.task_created  | CH-UT-000002 | workflow_engine|
|  14:05 mutation.approved     | CH-UT-000002 | rev_officer_chd |
|  14:05 tax.reassessment_start | CH-UT-000002 | workflow_engine|
|  14:06 tax.reassessed         | CH-UT-000002 | tax_officer_chd|
+--------------------------------------------------------------+
| EventFilter: [All events v] [Registration] [Mutation] [Tax]  |
+--------------------------------------------------------------+
```
Components: TopNav, SyncFeed, EventFilter

---

## Screen 13 — State Admin Panel
```
+--------------------------------------------------------------+
| TopNav:  [Admin: state_admin_tn]  [Logout]                   |
+--------------------------------------------------------------+
| StateOverview: Tamil Nadu | Parcels: 4 | Violations: 0 | ... |
+-------------------+-------------------+----------------------+
| CrossDeptSummary   | UserManagement     | AdapterView         |
|  pending mutations|  [list of officers]|  TN adapter config  |
|  pending tax      |  [add user]        |  (read-only)        |
+-------------------+-------------------+----------------------+
```
Components: TopNav, StateOverview, CrossDeptSummary, UserManagement, AdapterView

---

## Screen 14 — National / DoLR Analytics Dashboard
```
+--------------------------------------------------------------+
| TopNav:  [Admin: national_admin]  [Logout]                   |
+--------------------------------------------------------------+
| KpiRow: Parcels | Violations | PendingMutations | FraudFlags |
+--------------------------+-----------------------------------+
| StateBarChart (Recharts)  | ViolationTrendChart (Recharts)    |
+--------------------------+-----------------------------------+
| StateTable: state | parcels | violations | arrears            |
+--------------------------------------------------------------+
| AdapterEditor: select state -> edit field mapping/conversion |
+--------------------------------------------------------------+
```
Components: TopNav, KpiRow, StateBarChart, ViolationTrendChart, StateTable, AdapterEditor

---

## Screen 15 — Audit Trail Viewer
```
+--------------------------------------------------------------+
| TopNav:  [Audit]  ULPIN: CH-UT-000002                         |
+--------------------------------------------------------------+
| ChainIntegrityBanner: [OK] hash chain verified (8 entries)   |
+--------------------------------------------------------------+
| AuditTimeline                                                   |
|  2026-11-01 14:02 REG_OFF  REGISTER_DEED      hash=ab12..     |
|  2026-11-01 14:05 REV_OFF  APPROVE_MUTATION  hash=cd34..     |
|  2026-11-01 14:06 TAX_OFF  REASSESS_TAX      hash=ef56..     |
|  ... (citizen sees role+action+ts only, hash hidden)         |
+--------------------------------------------------------------+
| VerifyChainButton: recompute & compare hashes                |
+--------------------------------------------------------------+
```
Components: TopNav, ChainIntegrityBanner, AuditTimeline, VerifyChainButton

---

## Screen 16 — API Explorer
```
+--------------------------------------------------------------+
| TopNav:  [API Explorer]                                       |
+-------------------------------+------------------------------+
| EndpointList (OpenAPI)        | RequestPanel                  |
|  POST /auth/login             |  method path  [Send]          |
|  GET  /parcels/{ulpin}        |  headers: Authorization: ...   |
|  POST /registration           |  body: { ... }                |
|  POST /workflow/{id}/approve  |                               |
|  ...                          | ResponsePanel                 |
|                               |  status: 200  body: {...}     |
+-------------------------------+------------------------------+
```
Components: TopNav, EndpointList, RequestPanel, ResponsePanel
