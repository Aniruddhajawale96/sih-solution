# AI/ML Agent (Track A)
Owns: /backend/ml/*
- change_detection.py (OpenCV)
- fraud_score.py (scikit-learn Isolation Forest)
- ocr_extraction.py (pytesseract + regex)

For prototype speed, rule-based/simplified models are acceptable. Integrates into Zoning router (violation_flag) and Registration router (fraud_score). Exposed via /api/v1/ml/* routes per docs/RBAC_MATRIX.md.
