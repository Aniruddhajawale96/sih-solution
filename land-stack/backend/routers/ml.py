"""
routers/ml.py — Machine-Learning inference endpoints.

Endpoints
---------
POST /ml/change-detection  — Satellite image FAR change detection.
                              PLAN_OFF, STATE_ADMIN, NATL_ADMIN.
POST /ml/fraud-score        — Registration fraud / anomaly scoring.
                              REG_OFF, STATE_ADMIN, NATL_ADMIN.
POST /ml/ocr-extract        — OCR field extraction from RoR scan images.
                              REV_OFF, STATE_ADMIN, NATL_ADMIN.

Requirements: 10.1, 10.2, 10.3, 10.4
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.audit import write_audit
from core.database import get_db
from core.rbac import UserClaims, require_role
from core.schemas import Envelope, ok
from ml import change_detection, fraud_score, ocr_extraction
from models.parcel import Parcel
from models.zoning import Zoning

router = APIRouter()

# ---------------------------------------------------------------------------
# Role sets
# ---------------------------------------------------------------------------

_CHANGE_DETECTION_ROLES = ["PLAN_OFF", "STATE_ADMIN", "NATL_ADMIN"]
_FRAUD_SCORE_ROLES = ["REG_OFF", "STATE_ADMIN", "NATL_ADMIN"]
_OCR_EXTRACT_ROLES = ["REV_OFF", "STATE_ADMIN", "NATL_ADMIN"]


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class ChangeDetectionResponse(BaseModel):
    """Response payload for POST /ml/change-detection."""

    ulpin: str
    changed_area_sqm: float
    far_existing_est: float
    violation_flag: bool


class FraudScoreResponse(BaseModel):
    """Response payload for POST /ml/fraud-score."""

    ulpin: str
    deed_no: str
    fraud_score: float
    flagged: bool


class OcrExtractResponse(BaseModel):
    """Response payload for POST /ml/ocr-extract."""

    owner_name: str | None
    survey_or_khasra_no: str | None
    khatauni_no: str | None
    confidence: float
    raw_text: str


# ---------------------------------------------------------------------------
# Request schema (JSON body) for fraud-score
# ---------------------------------------------------------------------------

class FraudScoreRequest(BaseModel):
    ulpin: str
    deed_no: str
    transaction_value: float


# ---------------------------------------------------------------------------
# POST /ml/change-detection
# ---------------------------------------------------------------------------

@router.post(
    "/change-detection",
    response_model=Envelope[ChangeDetectionResponse],
    status_code=status.HTTP_200_OK,
    summary="Satellite image change detection (FAR violation check)",
)
async def detect_change(
    before_image: UploadFile = File(..., description="Satellite image before the event"),
    after_image: UploadFile = File(..., description="Satellite image after the event"),
    ulpin: str = Form(..., description="Universal Land Parcel Identification Number"),
    far_permitted: float = Form(..., description="Permitted FAR for the parcel"),
    user: UserClaims = Depends(require_role(_CHANGE_DETECTION_ROLES)),
    db: AsyncSession = Depends(get_db),
) -> Envelope[ChangeDetectionResponse]:
    """
    Compare before/after satellite images to detect FAR changes and flag violations.

    - Requires role PLAN_OFF, STATE_ADMIN, or NATL_ADMIN.
    - Fetches the parcel to obtain ``area_sqm``; returns 404 if not found.
    - Runs the OpenCV-based change detection model.
    - If a violation is detected (or FAR changed), updates the ``Zoning`` row's
      ``far_existing`` and ``violation_flag`` fields.
    - Writes an ML_CHANGE_DETECTION audit entry inside the same DB transaction
      before committing.
    """
    # Fetch parcel — 404 if missing
    parcel: Parcel | None = await db.get(Parcel, ulpin)
    if parcel is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Parcel {ulpin!r} not found",
        )

    # Read image bytes
    before_bytes = await before_image.read()
    after_bytes = await after_image.read()

    # Run ML inference
    result = change_detection.detect_changes(
        before_bytes=before_bytes,
        after_bytes=after_bytes,
        area_sqm=parcel.area_sqm,
        far_permitted=far_permitted,
    )

    # Update Zoning if violation flagged or FAR changed
    if result.violation_flag:
        zoning_result = await db.execute(
            select(Zoning).where(Zoning.ulpin == ulpin)
        )
        zoning: Zoning | None = zoning_result.scalar_one_or_none()
        if zoning is not None:
            zoning.far_existing = result.far_existing_est
            zoning.violation_flag = result.violation_flag

    # Audit — inside the same transaction; flush after as per contract
    await write_audit(
        db=db,
        actor_user=user.username,
        actor_role=user.role,
        action="ML_CHANGE_DETECTION",
        resource_type="parcel",
        resource_id=ulpin,
    )

    await db.commit()

    return ok(
        ChangeDetectionResponse(
            ulpin=ulpin,
            changed_area_sqm=result.changed_area_sqm,
            far_existing_est=result.far_existing_est,
            violation_flag=result.violation_flag,
        )
    )


# ---------------------------------------------------------------------------
# POST /ml/fraud-score
# ---------------------------------------------------------------------------

@router.post(
    "/fraud-score",
    response_model=Envelope[FraudScoreResponse],
    status_code=status.HTTP_200_OK,
    summary="Fraud / anomaly scoring for a registration transaction",
)
async def score_fraud(
    body: FraudScoreRequest,
    user: UserClaims = Depends(require_role(_FRAUD_SCORE_ROLES)),
    db: AsyncSession = Depends(get_db),
) -> Envelope[FraudScoreResponse]:
    """
    Score a deed registration transaction for fraud using an IsolationForest model.

    - Requires role REG_OFF, STATE_ADMIN, or NATL_ADMIN.
    - Fetches the parcel to obtain ``area_sqm``; returns 404 if not found.
    - Runs the scikit-learn fraud-scoring model.
    - Writes an ML_FRAUD_SCORE audit entry inside the same DB transaction
      before committing.
    """
    # Fetch parcel — 404 if missing
    parcel: Parcel | None = await db.get(Parcel, body.ulpin)
    if parcel is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Parcel {body.ulpin!r} not found",
        )

    # Run ML inference
    result = fraud_score.score_transaction(
        ulpin=body.ulpin,
        deed_no=body.deed_no,
        transaction_value=body.transaction_value,
        parcel_area_sqm=parcel.area_sqm,
    )

    # Audit — inside the same transaction; write_audit flushes internally
    await write_audit(
        db=db,
        actor_user=user.username,
        actor_role=user.role,
        action="ML_FRAUD_SCORE",
        resource_type="parcel",
        resource_id=body.ulpin,
    )

    await db.commit()

    return ok(
        FraudScoreResponse(
            ulpin=result.ulpin,
            deed_no=result.deed_no,
            fraud_score=result.fraud_score,
            flagged=result.flagged,
        )
    )


# ---------------------------------------------------------------------------
# POST /ml/ocr-extract
# ---------------------------------------------------------------------------

@router.post(
    "/ocr-extract",
    response_model=Envelope[OcrExtractResponse],
    status_code=status.HTTP_200_OK,
    summary="OCR field extraction from a RoR scan image",
)
async def ocr_extract(
    image: UploadFile = File(..., description="JPEG/PNG/TIFF scan of the Record of Rights"),
    state_code: str = Form(..., description="ISO state code (e.g. 'CH', 'TN')"),
    user: UserClaims = Depends(require_role(_OCR_EXTRACT_ROLES)),
    db: AsyncSession = Depends(get_db),
) -> Envelope[OcrExtractResponse]:
    """
    Extract structured land-record fields from a RoR document scan via OCR.

    - Requires role REV_OFF, STATE_ADMIN, or NATL_ADMIN.
    - Preprocesses the image with OpenCV and runs pytesseract.
    - Extracts owner name, survey/khasra number, and khatauni number.
    - Writes an ML_OCR_EXTRACT audit entry inside the same DB transaction
      before committing.
    """
    # Read image bytes
    image_bytes = await image.read()

    # Run ML inference (ValueError propagates as HTTP 422 via global handler)
    result = ocr_extraction.extract_ror_fields(
        image_bytes=image_bytes,
        state_code=state_code,
    )

    # Audit — inside the same transaction; write_audit flushes internally
    await write_audit(
        db=db,
        actor_user=user.username,
        actor_role=user.role,
        action="ML_OCR_EXTRACT",
        resource_type="state",
        resource_id=state_code,
    )

    await db.commit()

    return ok(
        OcrExtractResponse(
            owner_name=result.owner_name,
            survey_or_khasra_no=result.survey_or_khasra_no,
            khatauni_no=result.khatauni_no,
            confidence=result.confidence,
            raw_text=result.raw_text,
        )
    )
