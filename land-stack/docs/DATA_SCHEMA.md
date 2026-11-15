# Canonical Data Schema (LandStackRecord definitions)

All tables join on `ulpin`. This is the single source of truth — backend SQLAlchemy models, Pydantic schemas, and frontend TypeScript types must all match this exactly. Frozen after initial setup per docs/MULTI_AGENT_PARALLEL_WORKFLOW.md contract rules.

## parcel  (Base Layer)
| Field | Type | Notes |
|---|---|---|
| ulpin | string, PK | Universal join key across all tables |
| state_code | string | e.g. "CH", "TN" |
| district | string | |
| tehsil | string, nullable | rural-only in most states |
| village_or_city | string | |
| geom | Polygon, SRID 4326 | GeoAlchemy2 Geometry column |
| area_sqm | float | canonical unit — always sq. meters |
| survey_or_khasra_no | string | canonical name; native name mapped via adapter |
| source_system | string | e.g. "CHD-LandRecords-v2", "TN-ePatta-v3" |
| last_synced_at | timestamp | |

## ror  (Essential Layer — Record of Rights)
| Field | Type | Notes |
|---|---|---|
| ulpin | string, FK -> parcel | |
| owner_name | string | masked for CITIZEN public view |
| tenure_type | string | Freehold / Leasehold / Patta |
| khatauni_no | string | |
| land_use_type | string | Residential/Commercial/Agricultural |
| mutation_status | string | Clear / Pending |
| last_updated | date | |

## registration  (Essential Layer)
| Field | Type | Notes |
|---|---|---|
| ulpin | string, FK -> parcel | |
| deed_no | string | |
| deed_type | string | Sale / Gift / Lease |
| registration_date | date | |
| sro_office | string | |
| buyer | string | |
| seller | string | |
| transaction_value | int | hidden from public view entirely |
| stamp_duty_paid | bool | |

## encumbrance  (Essential Layer)
| Field | Type | Notes |
|---|---|---|
| ulpin | string, FK -> parcel | |
| type | string | Mortgage / Lien / Court Case |
| institution | string | shown publicly — transparency requirement |
| status | string | Active / Cleared |
| date | date | |

## zoning  (Essential Layer — Master Plan)
| Field | Type | Notes |
|---|---|---|
| ulpin | string, FK -> parcel | |
| master_plan_zone | string | Residential/Commercial/Agricultural |
| permissible_use | string | |
| far_permitted | float | Floor Area Ratio allowed |
| far_existing | float | Floor Area Ratio actually built (from ML/survey) |
| violation_flag | bool | true when far_existing > far_permitted |

## building_permission  (Essential Layer)
| Field | Type | Notes |
|---|---|---|
| ulpin | string, FK -> parcel | |
| approval_no | string | |
| approved_built_up_area | float | sq.m |
| approval_date | date | |
| status | string | Approved / Under Review / Rejected |
| architect_ref | string | |

## tax  (Essential Layer)
| Field | Type | Notes |
|---|---|---|
| ulpin | string, FK -> parcel | |
| assessment_id | string | |
| annual_tax | int | |
| last_paid_date | date | |
| payment_status | string | Paid / Overdue |
| arrears | int | shown publicly — public interest |

## audit_log  (Security — hash-chained)
| Field | Type | Notes |
|---|---|---|
| id | int, PK | |
| actor_user | string | |
| actor_role | string | one of 7 RBAC roles |
| action | string | e.g. "APPROVE_MUTATION" |
| resource_type | string | |
| resource_id | string | usually ulpin |
| timestamp | timestamp | |
| hash | string | SHA-256 of (prev_hash + row contents) |
| prev_hash | string | hash of previous row — forms tamper-evident chain |

## state_adapter_config  (Additional Layer — interoperability)
| Field | Type | Notes |
|---|---|---|
| state_code | string | |
| source_field_name | string | native field name in that state's system |
| canonical_field_name | string | maps to field names above |
| unit_conversion_factor | float | e.g. 4046.86 for acres -> sq.m |
| language_code | string | e.g. "en", "ta" |

## Entity Relationship Summary
```
parcel (1) ---- (0..1) ror
parcel (1) ---- (0..n) registration
parcel (1) ---- (0..n) encumbrance
parcel (1) ---- (0..1) zoning
parcel (1) ---- (0..n) building_permission
parcel (1) ---- (0..1) tax
parcel (1) ---- (0..n) audit_log (via resource_id)
state_code (1) -- (0..n) state_adapter_config
```
