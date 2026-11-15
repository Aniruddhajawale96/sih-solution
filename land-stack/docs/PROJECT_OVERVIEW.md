# Project Overview — Land Stack

## Problem (SIH PS #26014, Ministry of Rural Development / DoLR)
India's land records are fragmented across cadastral maps, Record of Rights (RoR), registration (sale deeds), encumbrance certificates, municipal master plans, building permissions, property tax rolls, and utility maps — each owned by a different department, on a different system, with no common key. This causes disputes, fraud, delayed approvals, and poor urban/rural planning.

## Objective
Build a GIS-based, ULPIN-anchored, interoperable Digital Public Infrastructure that:
- Unifies all land-related records under one spatial data model
- Organizes data into 3 layers: Base (cadastral), Essential (ownership/legal/fiscal), Additional (utilities/ML-derived insights)
- Serves both citizens (transparency, self-service) and officers (cross-department workflow automation)
- Works for both urban (Chandigarh) and rural (Tamil Nadu village) contexts without hardcoding state-specific formats
- Includes AI/ML for change detection, fraud scoring, and legacy document digitization
- Is secure (RBAC, audit trail, field-level masking) and produces a Standard Technical Document for national rollout

## Why ULPIN
The Unique Land Parcel Identification Number (ULPIN) is the one field every department's record can be mapped to, regardless of local naming (Khasra No. in Chandigarh, Survey No. in Tamil Nadu). It is the backbone join key of the entire platform.

## Pilots
1. **Chandigarh (Urban)** — Sector-based cadastral layout, English-language officialese, source_system "CHD-LandRecords-v2"
2. **Tamil Nadu Village — Thanjavur/Kallanai (Rural)** — Survey-number-based patta records, Tamil-language fields, source_system "TN-ePatta-v3", area recorded in acres (converted to sq.m via State Adapter)

## Core Innovation Points
- State Adapter pattern: config-driven field mapping + unit conversion
- Cross-department workflow automation: registration -> auto mutation -> auto tax reassessment, visible live on a Sync Monitor screen
- AI/ML: satellite before/after change detection for FAR violations, fraud/anomaly scoring on transactions, OCR digitization of legacy RoR scans
- Hash-chained audit log for tamper-evidence
- Public transparency with privacy: partial masking of owner PII while keeping encumbrance and tax-arrears data publicly visible

## Deliverables
1. Working prototype (docker-compose up, Chandigarh + TN pilot data)
2. Standard Technical Document (API standards, interoperability standards, data schemas, architecture, GIS standards, security, UI/UX guidelines, deployment/scalability)
3. Pitch deck / demo script
