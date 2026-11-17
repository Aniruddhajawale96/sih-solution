"""
tests/test_ml.py — Unit tests for routers/ml.py.

Validates: Requirements 12.1, 12.2

Covers:
  POST /ml/change-detection
    1. PLAN_OFF with valid images → 200; response has changed_area_sqm,
       far_existing_est, violation_flag; audit ML_CHANGE_DETECTION written.
    2. CITIZEN → 403.
    3. REV_OFF (wrong officer type) → 403.
    4. Unknown ULPIN → 404.

  POST /ml/fraud-score
    5. REG_OFF with valid input → 200; response has fraud_score, flagged;
       audit ML_FRAUD_SCORE written.
    6. CITIZEN → 403.
    7. Unknown ULPIN → 404.

  POST /ml/ocr-extract
    8. REV_OFF with valid image → 200; response has owner_name, confidence,
       raw_text; audit ML_OCR_EXTRACT written.
    9. CITIZEN → 403.

Tests use httpx.AsyncClient with FastAPI's ASGI transport.
No live PostgreSQL, OpenCV, pytesseract, or sklearn calls are made.
ML functions and write_audit are patched; get_db / get_redis are
overridden via dependency_overrides.
"""

from __future__ import annotations

import sys
import os
from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import httpx

# Allow importing backend/ modules directly when running pytest from the repo root.
_backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

from core.auth import create_access_token


# ---------------------------------------------------------------------------
# Lightweight stand-ins for ML result dataclasses.
# The router is patched so it never calls the real ML functions; these
# dataclasses just satisfy the router's attribute-access when constructing
# its response models.
# ---------------------------------------------------------------------------

@dataclass
class ChangeDetectionResult:
    changed_area_sqm: float
    far_existing_est: float
    violation_flag: bool


@dataclass
class FraudScoreResult:
    ulpin: str
    deed_no: str
    fraud_score: float
    flagged: bool


@dataclass
class OcrExtractionResult:
    owner_name: str | None
    survey_or_khasra_no: str | None
    khatauni_no: str | None
    confidence: float
    raw_text: str


# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------

def _make_token(role: str, jurisdiction: str | None = None) -> str:
    return create_access_token(
        {"sub": f"user_{role.lower()}", "role": role, "jurisdiction": jurisdiction}
    )


def _auth_headers(role: str, jurisdiction: str | None = None) -> dict[str, str]:
    return {"Authorization": f"Bearer {_make_token(role, jurisdiction)}"}


# ---------------------------------------------------------------------------
# Dependency override helpers
# ---------------------------------------------------------------------------

def _make_db_override(db_mock):
    """Async-generator override for get_db."""
    async def _override():
        yield db_mock
    return _override


# ---------------------------------------------------------------------------
# Minimal Parcel stub
# ---------------------------------------------------------------------------

class _FakeParcel:
    def __init__(self, ulpin: str = "MH-MUM-001", area_sqm: float = 250.0):
        self.ulpin = ulpin
        self.area_sqm = area_sqm
        self.state_code = "MH"


# ---------------------------------------------------------------------------
# DB / Redis mock factories
# ---------------------------------------------------------------------------

def _make_db_mock(parcel: _FakeParcel | None = None) -> AsyncMock:
    """Return an AsyncMock that quacks like an AsyncSession."""
    db = AsyncMock()
    db.get = AsyncMock(return_value=parcel)

    scalar_result = MagicMock()
    scalar_result.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=scalar_result)

    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.add = MagicMock()
    db.refresh = AsyncMock()
    return db


def _make_redis_mock() -> AsyncMock:
    redis = AsyncMock()
    redis.exists = AsyncMock(return_value=0)
    return redis


# ---------------------------------------------------------------------------
# Minimal valid PNG bytes for multipart file uploads.
# The ML functions are patched, so the actual pixel content is irrelevant;
# we just need a non-empty bytes object that httpx will send as a file.
# ---------------------------------------------------------------------------

_MINIMAL_PNG = bytes([
    0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,  # PNG signature
    0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,  # IHDR length + type
    0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,  # width=1, height=1
    0x08, 0x02, 0x00, 0x00, 0x00, 0x90, 0x77, 0x53,  # bit-depth, color-type, CRC
    0xDE, 0x00, 0x00, 0x00, 0x0C, 0x49, 0x44, 0x41,  # IDAT length + type
    0x54, 0x08, 0xD7, 0x63, 0xF8, 0xCF, 0xC0, 0x00,  # IDAT data (compressed)
    0x00, 0x00, 0x02, 0x00, 0x01, 0xE2, 0x21, 0xBC,  # IDAT data + CRC
    0x33, 0x00, 0x00, 0x00, 0x00, 0x49, 0x45, 0x4E,  # IEND length + type
    0x44, 0xAE, 0x42, 0x60, 0x82,                    # IEND CRC
])


# ---------------------------------------------------------------------------
# Shared app/client setup helper
# ---------------------------------------------------------------------------

def _setup_app(parcel: _FakeParcel | None):
    """Override get_db / get_redis and return (app, db_mock, redis_mock)."""
    from main import app
    from core.database import get_db
    from core.redis_client import get_redis

    db_mock = _make_db_mock(parcel)
    redis_mock = _make_redis_mock()

    app.dependency_overrides[get_db] = _make_db_override(db_mock)
    app.dependency_overrides[get_redis] = lambda: redis_mock

    return app, db_mock, redis_mock


# ===========================================================================
# POST /ml/change-detection
# ===========================================================================

@pytest.mark.anyio
async def test_change_detection_plan_off_valid_200(anyio_backend):
    """PLAN_OFF with valid multipart images → 200; required fields present; audit written."""
    parcel = _FakeParcel()
    app, db_mock, _ = _setup_app(parcel)

    fake_result = ChangeDetectionResult(
        changed_area_sqm=50.0,
        far_existing_est=0.2,
        violation_flag=False,
    )

    try:
        with patch("ml.change_detection.detect_changes", return_value=fake_result) as mock_detect, \
             patch("routers.ml.write_audit", new_callable=AsyncMock) as mock_audit:
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as ac:
                resp = await ac.post(
                    "/api/v1/ml/change-detection",
                    headers=_auth_headers("PLAN_OFF"),
                    files={
                        "before_image": ("before.png", _MINIMAL_PNG, "image/png"),
                        "after_image": ("after.png", _MINIMAL_PNG, "image/png"),
                    },
                    data={
                        "ulpin": parcel.ulpin,
                        "far_permitted": "2.5",
                    },
                )
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["success"] is True
    data = body["data"]
    assert "changed_area_sqm" in data
    assert "far_existing_est" in data
    assert "violation_flag" in data
    assert data["changed_area_sqm"] == 50.0
    assert data["far_existing_est"] == 0.2
    assert data["violation_flag"] is False

    mock_detect.assert_called_once()

    mock_audit.assert_called_once()
    _, audit_kwargs = mock_audit.call_args
    assert audit_kwargs.get("action") == "ML_CHANGE_DETECTION"
    assert audit_kwargs.get("resource_type") == "parcel"
    assert audit_kwargs.get("resource_id") == parcel.ulpin


@pytest.mark.anyio
async def test_change_detection_citizen_403(anyio_backend):
    """CITIZEN caller → 403 on /ml/change-detection."""
    parcel = _FakeParcel()
    app, _, _ = _setup_app(parcel)

    try:
        with patch("ml.change_detection.detect_changes") as mock_detect, \
             patch("routers.ml.write_audit", new_callable=AsyncMock):
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as ac:
                resp = await ac.post(
                    "/api/v1/ml/change-detection",
                    headers=_auth_headers("CITIZEN"),
                    files={
                        "before_image": ("before.png", _MINIMAL_PNG, "image/png"),
                        "after_image": ("after.png", _MINIMAL_PNG, "image/png"),
                    },
                    data={"ulpin": parcel.ulpin, "far_permitted": "2.5"},
                )
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 403
    mock_detect.assert_not_called()


@pytest.mark.anyio
async def test_change_detection_rev_off_403(anyio_backend):
    """REV_OFF (wrong officer type for change-detection) → 403."""
    parcel = _FakeParcel()
    app, _, _ = _setup_app(parcel)

    try:
        with patch("ml.change_detection.detect_changes") as mock_detect, \
             patch("routers.ml.write_audit", new_callable=AsyncMock):
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as ac:
                resp = await ac.post(
                    "/api/v1/ml/change-detection",
                    headers=_auth_headers("REV_OFF"),
                    files={
                        "before_image": ("before.png", _MINIMAL_PNG, "image/png"),
                        "after_image": ("after.png", _MINIMAL_PNG, "image/png"),
                    },
                    data={"ulpin": parcel.ulpin, "far_permitted": "2.5"},
                )
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 403
    mock_detect.assert_not_called()


@pytest.mark.anyio
async def test_change_detection_unknown_ulpin_404(anyio_backend):
    """Unknown ULPIN → 404 on /ml/change-detection."""
    app, _, _ = _setup_app(parcel=None)

    try:
        with patch("ml.change_detection.detect_changes") as mock_detect, \
             patch("routers.ml.write_audit", new_callable=AsyncMock):
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as ac:
                resp = await ac.post(
                    "/api/v1/ml/change-detection",
                    headers=_auth_headers("PLAN_OFF"),
                    files={
                        "before_image": ("before.png", _MINIMAL_PNG, "image/png"),
                        "after_image": ("after.png", _MINIMAL_PNG, "image/png"),
                    },
                    data={"ulpin": "UNKNOWN-999", "far_permitted": "2.5"},
                )
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 404
    mock_detect.assert_not_called()


# ===========================================================================
# POST /ml/fraud-score
# ===========================================================================

@pytest.mark.anyio
async def test_fraud_score_reg_off_valid_200(anyio_backend):
    """REG_OFF with valid input → 200; fraud_score and flagged present; audit written."""
    parcel = _FakeParcel()
    app, db_mock, _ = _setup_app(parcel)

    fake_result = FraudScoreResult(
        ulpin=parcel.ulpin,
        deed_no="DEED-2024-001",
        fraud_score=-0.05,
        flagged=False,
    )

    try:
        with patch("ml.fraud_score.score_transaction", return_value=fake_result) as mock_score, \
             patch("routers.ml.write_audit", new_callable=AsyncMock) as mock_audit:
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as ac:
                resp = await ac.post(
                    "/api/v1/ml/fraud-score",
                    headers=_auth_headers("REG_OFF"),
                    json={
                        "ulpin": parcel.ulpin,
                        "deed_no": "DEED-2024-001",
                        "transaction_value": 500_000.0,
                    },
                )
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["success"] is True
    data = body["data"]
    assert "fraud_score" in data
    assert "flagged" in data
    assert data["fraud_score"] == -0.05
    assert data["flagged"] is False

    mock_score.assert_called_once()

    mock_audit.assert_called_once()
    _, audit_kwargs = mock_audit.call_args
    assert audit_kwargs.get("action") == "ML_FRAUD_SCORE"
    assert audit_kwargs.get("resource_type") == "parcel"
    assert audit_kwargs.get("resource_id") == parcel.ulpin


@pytest.mark.anyio
async def test_fraud_score_citizen_403(anyio_backend):
    """CITIZEN caller → 403 on /ml/fraud-score."""
    parcel = _FakeParcel()
    app, _, _ = _setup_app(parcel)

    try:
        with patch("ml.fraud_score.score_transaction") as mock_score, \
             patch("routers.ml.write_audit", new_callable=AsyncMock):
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as ac:
                resp = await ac.post(
                    "/api/v1/ml/fraud-score",
                    headers=_auth_headers("CITIZEN"),
                    json={
                        "ulpin": parcel.ulpin,
                        "deed_no": "DEED-2024-001",
                        "transaction_value": 500_000.0,
                    },
                )
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 403
    mock_score.assert_not_called()


@pytest.mark.anyio
async def test_fraud_score_unknown_ulpin_404(anyio_backend):
    """Unknown ULPIN → 404 on /ml/fraud-score."""
    app, _, _ = _setup_app(parcel=None)

    try:
        with patch("ml.fraud_score.score_transaction") as mock_score, \
             patch("routers.ml.write_audit", new_callable=AsyncMock):
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as ac:
                resp = await ac.post(
                    "/api/v1/ml/fraud-score",
                    headers=_auth_headers("REG_OFF"),
                    json={
                        "ulpin": "UNKNOWN-999",
                        "deed_no": "DEED-2024-001",
                        "transaction_value": 500_000.0,
                    },
                )
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 404
    mock_score.assert_not_called()


# ===========================================================================
# POST /ml/ocr-extract
# ===========================================================================

@pytest.mark.anyio
async def test_ocr_extract_rev_off_valid_200(anyio_backend):
    """REV_OFF with valid image → 200; owner_name, confidence, raw_text present; audit written."""
    parcel = _FakeParcel()
    app, _, _ = _setup_app(parcel)

    fake_result = OcrExtractionResult(
        owner_name="Ramesh Kumar",
        survey_or_khasra_no="S/42",
        khatauni_no="K/7",
        confidence=87.5,
        raw_text="Owner: Ramesh Kumar Survey No: S/42 Khatauni: K/7",
    )

    try:
        with patch("ml.ocr_extraction.extract_ror_fields", return_value=fake_result) as mock_ocr, \
             patch("routers.ml.write_audit", new_callable=AsyncMock) as mock_audit:
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as ac:
                resp = await ac.post(
                    "/api/v1/ml/ocr-extract",
                    headers=_auth_headers("REV_OFF"),
                    files={
                        "image": ("ror.png", _MINIMAL_PNG, "image/png"),
                    },
                    data={"state_code": "MH"},
                )
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["success"] is True
    data = body["data"]
    assert "owner_name" in data
    assert "confidence" in data
    assert "raw_text" in data
    assert data["owner_name"] == "Ramesh Kumar"
    assert data["confidence"] == 87.5
    assert "Ramesh Kumar" in data["raw_text"]

    mock_ocr.assert_called_once()

    mock_audit.assert_called_once()
    _, audit_kwargs = mock_audit.call_args
    assert audit_kwargs.get("action") == "ML_OCR_EXTRACT"
    assert audit_kwargs.get("resource_type") == "state"
    assert audit_kwargs.get("resource_id") == "MH"


@pytest.mark.anyio
async def test_ocr_extract_citizen_403(anyio_backend):
    """CITIZEN caller → 403 on /ml/ocr-extract."""
    parcel = _FakeParcel()
    app, _, _ = _setup_app(parcel)

    try:
        with patch("ml.ocr_extraction.extract_ror_fields") as mock_ocr, \
             patch("routers.ml.write_audit", new_callable=AsyncMock):
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as ac:
                resp = await ac.post(
                    "/api/v1/ml/ocr-extract",
                    headers=_auth_headers("CITIZEN"),
                    files={
                        "image": ("ror.png", _MINIMAL_PNG, "image/png"),
                    },
                    data={"state_code": "MH"},
                )
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 403
    mock_ocr.assert_not_called()
