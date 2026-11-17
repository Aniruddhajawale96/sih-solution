"""
ml/change_detection.py — Satellite image change detection for FAR violation estimation.

Uses OpenCV to compare before/after images of a parcel and compute the changed
pixel area, then estimates FAR and flags violations.

Public API
----------
detect_changes(before_bytes, after_bytes, area_sqm, far_permitted)
    -> ChangeDetectionResult

ChangeDetectionResult
    changed_area_sqm : float   – estimated changed area in square metres
    far_existing_est : float   – changed_area_sqm / area_sqm (FAR estimate)
    violation_flag   : bool    – True when far_existing_est > far_permitted
"""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

# Binary threshold value: pixels whose absolute difference exceeds this value
# are classified as "changed".  128 (half of 255) is a reasonable default for
# grayscale satellite imagery.
_THRESHOLD = 128


@dataclass
class ChangeDetectionResult:
    """Result returned by :func:`detect_changes`."""

    changed_area_sqm: float
    far_existing_est: float
    violation_flag: bool


def _decode_image(raw: bytes, label: str) -> np.ndarray:
    """
    Decode raw bytes into a BGR NumPy array.

    Parameters
    ----------
    raw   : bytes  – JPEG/PNG/TIFF image bytes.
    label : str    – Human-readable label used in error messages.

    Raises
    ------
    ValueError
        If *raw* cannot be decoded as a valid image.
    """
    if not raw:
        raise ValueError(f"{label}: image bytes are empty")

    buf = np.frombuffer(raw, dtype=np.uint8)
    img = cv2.imdecode(buf, cv2.IMREAD_COLOR)

    if img is None:
        raise ValueError(
            f"{label}: could not decode image bytes — data may be corrupt or "
            "in an unsupported format"
        )

    return img


def detect_changes(
    before_bytes: bytes,
    after_bytes: bytes,
    area_sqm: float,
    far_permitted: float,
) -> ChangeDetectionResult:
    """
    Compare two satellite images of the same parcel and estimate FAR.

    Algorithm
    ---------
    1. Decode both byte arrays into BGR images.
    2. Resize the *after* image to match the *before* image so ``cv2.absdiff``
       operates on aligned arrays.
    3. Convert to grayscale and compute absolute pixel-wise difference.
    4. Apply binary threshold to isolate significantly changed pixels.
    5. Find contours and sum contour areas to get the total changed pixel count.
    6. Scale pixel count to square metres using the parcel's known area:
       ``sqm_per_pixel = area_sqm / (width * height)``
    7. Estimate FAR: ``far_existing_est = changed_area_sqm / area_sqm``
       (guarded against zero division).
    8. Set ``violation_flag = far_existing_est > far_permitted``.

    Parameters
    ----------
    before_bytes  : bytes  – Raw image bytes of the parcel before the event.
    after_bytes   : bytes  – Raw image bytes of the parcel after the event.
    area_sqm      : float  – Known area of the parcel in square metres.
    far_permitted : float  – Maximum permitted Floor Area Ratio for the parcel.

    Returns
    -------
    ChangeDetectionResult

    Raises
    ------
    ValueError
        If either image cannot be decoded, or if *area_sqm* is not positive.
    """
    # Validate inputs ---------------------------------------------------------
    before = _decode_image(before_bytes, "before_image")
    after = _decode_image(after_bytes, "after_image")

    if area_sqm <= 0:
        raise ValueError(
            f"area_sqm must be a positive number, got {area_sqm!r}"
        )

    # Align images to the same spatial extent --------------------------------
    # Resize `after` to match `before`'s dimensions; use INTER_AREA for
    # down-scaling (most common) and INTER_LINEAR for up-scaling.
    h_before, w_before = before.shape[:2]
    h_after, w_after = after.shape[:2]

    if (h_before, w_before) != (h_after, w_after):
        interp = cv2.INTER_AREA if (h_after > h_before or w_after > w_before) else cv2.INTER_LINEAR
        after = cv2.resize(after, (w_before, h_before), interpolation=interp)

    # Compute absolute difference on grayscale --------------------------------
    gray_before = cv2.cvtColor(before, cv2.COLOR_BGR2GRAY)
    gray_after = cv2.cvtColor(after, cv2.COLOR_BGR2GRAY)

    diff = cv2.absdiff(gray_before, gray_after)

    # Threshold to binary mask ------------------------------------------------
    _, binary_mask = cv2.threshold(diff, _THRESHOLD, 255, cv2.THRESH_BINARY)

    # Sum changed pixel area via contours ------------------------------------
    contours, _ = cv2.findContours(
        binary_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )

    changed_pixels: float = sum(cv2.contourArea(c) for c in contours)

    # Scale pixels → square metres -------------------------------------------
    total_pixels = float(w_before * h_before)
    sqm_per_pixel = area_sqm / total_pixels  # always safe: area_sqm > 0 and pixels > 0
    changed_area_sqm = changed_pixels * sqm_per_pixel

    # Estimate FAR and check violation ----------------------------------------
    far_existing_est = changed_area_sqm / area_sqm if area_sqm > 0 else 0.0
    violation_flag = far_existing_est > far_permitted

    return ChangeDetectionResult(
        changed_area_sqm=changed_area_sqm,
        far_existing_est=far_existing_est,
        violation_flag=violation_flag,
    )
