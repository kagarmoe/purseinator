from __future__ import annotations

import importlib.util

import pytest

numpy_available = importlib.util.find_spec("numpy") is not None
skip_no_gpu = pytest.mark.skipif(
    not numpy_available,
    reason="requires gpu extras: pip install -e '.[gpu]'"
)


@skip_no_gpu
def test_estimate_condition_returns_score():
    import numpy as np
    from app.enrich.condition import estimate_condition
    fake_image = np.zeros((224, 224, 3), dtype=np.uint8)
    result = estimate_condition(fake_image)
    assert "score" in result
    assert 0.0 <= result["score"] <= 1.0


@skip_no_gpu
def test_estimate_condition_returns_label():
    import numpy as np
    from app.enrich.condition import estimate_condition
    fake_image = np.zeros((224, 224, 3), dtype=np.uint8)
    result = estimate_condition(fake_image)
    assert result["label"] in ("excellent", "good", "fair", "poor")


@skip_no_gpu
def test_estimate_condition_returns_details():
    import numpy as np
    from app.enrich.condition import estimate_condition
    fake_image = np.zeros((224, 224, 3), dtype=np.uint8)
    result = estimate_condition(fake_image)
    assert "details" in result
    for key in ("wear", "scratches", "staining"):
        assert key in result["details"]
        assert 0.0 <= result["details"][key] <= 1.0


@skip_no_gpu
def test_score_to_label_excellent():
    from app.enrich.condition import score_to_label
    assert score_to_label(0.90) == "excellent"


@skip_no_gpu
def test_score_to_label_good():
    from app.enrich.condition import score_to_label
    assert score_to_label(0.70) == "good"


@skip_no_gpu
def test_score_to_label_fair():
    from app.enrich.condition import score_to_label
    assert score_to_label(0.50) == "fair"


@skip_no_gpu
def test_score_to_label_poor():
    from app.enrich.condition import score_to_label
    assert score_to_label(0.20) == "poor"
