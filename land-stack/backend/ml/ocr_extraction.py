"""
ml/ocr_extraction.py — OCR field extraction from legacy RoR scan images.

Preprocesses an image with OpenCV (denoise + adaptive threshold), runs
pytesseract to extract text with per-word confidence scores, then applies
regex patterns to pull structured land-record fields.

Public API
----------
extract_ror_fields(image_bytes, state_code) -> OcrExtractionResult

OcrExtractionResult
    owner_name          : str | None  – name after Owner/Name/Khatedar keyword
    survey_or_khasra_no : str | None  – survey / khasra number
    khatauni_no         : str | None  – khatauni / account number
    confidence          : float       – mean pytesseract word confidence (0–100)
    raw_text            : str         – full OCR output string
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import cv2
import numpy as np
from PIL import Image
from pytesseract import Output
import pytesseract


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class OcrExtractionResult:
    """Structured OCR result returned by :func:`extract_ror_fields`."""

    owner_name: str | None
    survey_or_khasra_no: str | None
    khatauni_no: str | None
    confidence: float
    raw_text: str


# ---------------------------------------------------------------------------
# Regex patterns for RoR field extraction
# ---------------------------------------------------------------------------

# Matches the owner / khatedar name that follows an identifying keyword.
# Captures a sequence of letters, spaces, and dots (up to 60 chars) so that
# the regex does not bleed into the next field on the same line.
_PATTERN_OWNER = re.compile(
    r"(?:owner|name|khatedar)[:\s]+([A-Za-z\s\.]{1,60})",
    re.IGNORECASE,
)

# Matches survey number or khasra number.
_PATTERN_SURVEY = re.compile(
    r"(?:survey|khasra|kh\.?\s*no)[:\s.#]+(\d+[\w/\-]*)",
    re.IGNORECASE,
)

# Matches khatauni / account number.
_PATTERN_KHATAUNI = re.compile(
    r"(?:khatauni|account)[:\s.#]+(\d+[\w/\-]*)",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _preprocess_image(image_bytes: bytes) -> Image.Image:
    """
    Decode and preprocess raw image bytes for optimal OCR quality.

    Pipeline
    --------
    1. Decode bytes → BGR NumPy array via ``cv2.imdecode``.
    2. Convert to grayscale.
    3. Denoise with ``cv2.fastNlMeansDenoising`` (h=10).
    4. Apply adaptive Gaussian threshold to produce a clean binary image.
    5. Wrap the result in a PIL Image for pytesseract.

    Parameters
    ----------
    image_bytes : bytes – Raw JPEG/PNG/TIFF bytes of the RoR scan.

    Returns
    -------
    PIL.Image.Image – Preprocessed grayscale image ready for OCR.

    Raises
    ------
    ValueError
        If *image_bytes* is empty or cannot be decoded as a valid image.
    """
    if not image_bytes:
        raise ValueError(
            "image_bytes is empty — supply raw JPEG/PNG/TIFF bytes of the RoR scan"
        )

    # Step 1: bytes → BGR NumPy array
    buf = np.frombuffer(image_bytes, dtype=np.uint8)
    img_bgr = cv2.imdecode(buf, cv2.IMREAD_COLOR)

    if img_bgr is None:
        raise ValueError(
            "Could not decode image_bytes — data may be corrupt or in an "
            "unsupported format (expected JPEG, PNG, or TIFF)"
        )

    # Step 2: BGR → grayscale
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)

    # Step 3: denoise (h=10 is a good default for scanned documents)
    denoised = cv2.fastNlMeansDenoising(gray, h=10)

    # Step 4: adaptive Gaussian threshold → clean binary image
    binary = cv2.adaptiveThreshold(
        denoised,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        blockSize=11,
        C=2,
    )

    # Step 5: NumPy array → PIL Image for pytesseract
    return Image.fromarray(binary)


def _extract_field(pattern: re.Pattern[str], text: str) -> str | None:
    """
    Apply *pattern* to *text* and return the first capture group, stripped.

    Returns ``None`` if no match is found — never raises.
    """
    match = pattern.search(text)
    if match:
        return match.group(1).strip() or None
    return None


def _mean_confidence(conf_values: list[int | str]) -> float:
    """
    Compute the mean of non-negative, non-zero pytesseract confidence scores.

    pytesseract returns -1 for lines/blocks that are not words; those are
    excluded from the mean.  If all values are non-positive the confidence
    is 0.0.

    Parameters
    ----------
    conf_values : list – ``conf`` list from pytesseract ``image_to_data`` dict.

    Returns
    -------
    float – Mean confidence in the range [0, 100].
    """
    positive: list[float] = [
        float(c) for c in conf_values if isinstance(c, (int, float)) and c > 0
    ]
    if not positive:
        return 0.0
    return sum(positive) / len(positive)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def extract_ror_fields(
    image_bytes: bytes,
    state_code: str,  # noqa: ARG001 — reserved for state-specific tuning
) -> OcrExtractionResult:
    """
    Extract structured land-record fields from a RoR scan image.

    Parameters
    ----------
    image_bytes : bytes – Raw image bytes (JPEG, PNG, or TIFF) of the scan.
    state_code  : str   – ISO state code (e.g. ``"CH"``, ``"TN"``); reserved
                          for future state-specific OCR tuning (language hints,
                          custom regex).

    Returns
    -------
    OcrExtractionResult
        ``owner_name``, ``survey_or_khasra_no``, ``khatauni_no`` are ``None``
        when the corresponding pattern finds no match.  ``confidence`` is the
        mean pytesseract word confidence (0–100).  ``raw_text`` is the full
        OCR string.

    Raises
    ------
    ValueError
        If *image_bytes* is empty or cannot be decoded as a valid image.
    """
    # Preprocess — raises ValueError for corrupt / empty bytes
    pil_image = _preprocess_image(image_bytes)

    # Run OCR with per-word confidence scores
    ocr_data = pytesseract.image_to_data(pil_image, output_type=Output.DICT)

    # Build the full text string from individual word tokens
    raw_text = " ".join(
        word for word in ocr_data.get("text", []) if word.strip()
    )

    # Compute mean confidence from non-zero scores
    confidence = _mean_confidence(ocr_data.get("conf", []))

    # Extract fields via regex
    owner_name = _extract_field(_PATTERN_OWNER, raw_text)
    survey_or_khasra_no = _extract_field(_PATTERN_SURVEY, raw_text)
    khatauni_no = _extract_field(_PATTERN_KHATAUNI, raw_text)

    return OcrExtractionResult(
        owner_name=owner_name,
        survey_or_khasra_no=survey_or_khasra_no,
        khatauni_no=khatauni_no,
        confidence=confidence,
        raw_text=raw_text,
    )
