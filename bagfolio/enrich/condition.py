from __future__ import annotations

import numpy as np


def score_to_label(score: float) -> str:
    if score >= 0.85:
        return "excellent"
    if score >= 0.65:
        return "good"
    if score >= 0.40:
        return "fair"
    return "poor"


def estimate_condition(image: np.ndarray) -> dict:
    """Estimate handbag condition from photo.

    MVP placeholder — returns a default that signals "needs human review".
    Will be replaced with a fine-tuned vision model.
    """
    return {
        "score": 0.5,
        "label": score_to_label(0.5),
        "details": {
            "wear": 0.5,
            "scratches": 0.5,
            "staining": 0.5,
        },
    }
