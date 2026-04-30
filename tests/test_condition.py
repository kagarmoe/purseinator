from __future__ import annotations

import numpy as np

from purseinator.enrich.condition import estimate_condition, score_to_label


def test_estimate_condition_returns_score():
    fake_image = np.zeros((224, 224, 3), dtype=np.uint8)
    result = estimate_condition(fake_image)
    assert "score" in result
    assert 0.0 <= result["score"] <= 1.0


def test_estimate_condition_returns_label():
    fake_image = np.zeros((224, 224, 3), dtype=np.uint8)
    result = estimate_condition(fake_image)
    assert result["label"] in ("excellent", "good", "fair", "poor")


def test_estimate_condition_returns_details():
    fake_image = np.zeros((224, 224, 3), dtype=np.uint8)
    result = estimate_condition(fake_image)
    assert "details" in result
    for key in ("wear", "scratches", "staining"):
        assert key in result["details"]
        assert 0.0 <= result["details"][key] <= 1.0


def test_score_to_label_excellent():
    assert score_to_label(0.90) == "excellent"


def test_score_to_label_good():
    assert score_to_label(0.70) == "good"


def test_score_to_label_fair():
    assert score_to_label(0.50) == "fair"


def test_score_to_label_poor():
    assert score_to_label(0.20) == "poor"
