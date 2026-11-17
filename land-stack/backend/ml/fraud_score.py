"""
backend/ml/fraud_score.py — Fraud / Anomaly Scoring using scikit-learn IsolationForest.

Loads a pre-trained IsolationForest from a pickle file on first import.
If the file is absent or corrupt, trains a new model on a small synthetic seed
dataset and saves it back to the same path.

Feature vector (4 features):
    [transaction_value, log(transaction_value + 1), area_sqm, value_per_sqm]

Requirements ref: 10.2
"""

from __future__ import annotations

import logging
import math
import os
import pickle
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from sklearn.ensemble import IsolationForest

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Default model path — override via env var FRAUD_MODEL_PATH for tests /
# container deployments.
# ---------------------------------------------------------------------------
_DEFAULT_MODEL_PATH = Path(__file__).parent / "fraud_model.pkl"
_MODEL_PATH = Path(os.environ.get("FRAUD_MODEL_PATH", str(_DEFAULT_MODEL_PATH)))


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass
class FraudScoreResult:
    ulpin: str
    deed_no: str
    fraud_score: float
    flagged: bool


# ---------------------------------------------------------------------------
# Synthetic seed data helpers
# ---------------------------------------------------------------------------


def _generate_seed_features(rng: np.random.Generator) -> np.ndarray:
    """Return a (210, 4) feature matrix for initial model training."""
    # 200 "normal" transactions
    tv_normal = rng.uniform(100_000, 5_000_000, size=200)
    area_normal = rng.uniform(50, 500, size=200)

    # 10 "anomalous" transactions
    tv_anomaly = rng.uniform(50_000_000, 100_000_000, size=10)
    area_anomaly = rng.uniform(10, 30, size=10)

    tv = np.concatenate([tv_normal, tv_anomaly])
    area = np.concatenate([area_normal, area_anomaly])

    vpqm = tv / area  # area is always > 0 here
    log_tv = np.log(tv + 1)

    return np.column_stack([tv, log_tv, area, vpqm])


def _train_and_save(model_path: Path) -> IsolationForest:
    """Train a fresh IsolationForest on synthetic data and persist it."""
    logger.info("Training new IsolationForest model (seed data)...")
    rng = np.random.default_rng(42)
    X = _generate_seed_features(rng)

    model = IsolationForest(
        n_estimators=100,
        contamination=10 / 210,  # ~10 anomalies out of 210
        random_state=42,
    )
    model.fit(X)

    try:
        model_path.parent.mkdir(parents=True, exist_ok=True)
        with open(model_path, "wb") as fh:
            pickle.dump(model, fh, protocol=pickle.HIGHEST_PROTOCOL)
        logger.info("Saved IsolationForest model to %s", model_path)
    except Exception as exc:  # pragma: no cover
        logger.warning("Could not save model to %s: %s", model_path, exc)

    return model


# ---------------------------------------------------------------------------
# Module-level model loading
# ---------------------------------------------------------------------------


def _load_model(model_path: Path) -> IsolationForest:
    """Load model from *model_path*, training from scratch on any error."""
    if model_path.exists():
        try:
            with open(model_path, "rb") as fh:
                model = pickle.load(fh)
            if not isinstance(model, IsolationForest):
                raise TypeError(f"Unexpected pickle contents: {type(model)}")
            logger.info("Loaded IsolationForest model from %s", model_path)
            return model
        except Exception as exc:
            logger.warning(
                "Failed to load model from %s (%s); retraining.", model_path, exc
            )
    else:
        logger.info(
            "Model file not found at %s; training from seed data.", model_path
        )

    return _train_and_save(model_path)


# Module-level singleton — loaded once at import time.
_model: IsolationForest = _load_model(_MODEL_PATH)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def _build_features(transaction_value: float, parcel_area_sqm: float) -> np.ndarray:
    """Return a (1, 4) feature array for a single transaction."""
    value_per_sqm = transaction_value / parcel_area_sqm
    log_tv = math.log(transaction_value + 1)
    return np.array([[transaction_value, log_tv, parcel_area_sqm, value_per_sqm]])


def score_transaction(
    ulpin: str,
    deed_no: str,
    transaction_value: float,
    parcel_area_sqm: float,
) -> FraudScoreResult:
    """Score a registration transaction for fraud / anomaly.

    Parameters
    ----------
    ulpin:
        Universal Land Parcel Identification Number.
    deed_no:
        Registration deed number.
    transaction_value:
        Declared transaction value in INR (must be > 0).
    parcel_area_sqm:
        Parcel area in square metres (must be > 0).

    Returns
    -------
    FraudScoreResult
        Contains the raw ``fraud_score`` (IsolationForest anomaly score) and a
        boolean ``flagged`` flag (True when score < −0.1).

    Raises
    ------
    ValueError
        If ``transaction_value`` ≤ 0 or ``parcel_area_sqm`` ≤ 0.
    """
    if transaction_value <= 0:
        raise ValueError(
            f"transaction_value must be > 0, got {transaction_value!r}"
        )
    if parcel_area_sqm <= 0:
        raise ValueError(
            f"parcel_area_sqm must be > 0, got {parcel_area_sqm!r}"
        )

    features = _build_features(transaction_value, parcel_area_sqm)
    score: float = float(_model.score_samples(features)[0])
    flagged: bool = score < -0.1

    return FraudScoreResult(
        ulpin=ulpin,
        deed_no=deed_no,
        fraud_score=score,
        flagged=flagged,
    )
