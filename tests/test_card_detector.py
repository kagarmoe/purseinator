from __future__ import annotations

import numpy as np

from purseinator.ingest.card_detector import is_delimiter_card


def test_neon_green_card_detected():
    green_image = np.zeros((100, 100, 3), dtype=np.uint8)
    green_image[:, :] = [0, 255, 0]  # BGR green
    assert is_delimiter_card(green_image) is True


def test_bag_photo_not_detected():
    brown_image = np.zeros((100, 100, 3), dtype=np.uint8)
    brown_image[:, :] = [50, 100, 150]  # BGR brownish
    assert is_delimiter_card(brown_image) is False


def test_partial_green_not_detected():
    mixed = np.zeros((100, 100, 3), dtype=np.uint8)
    mixed[:10, :] = [0, 255, 0]  # Only 10% green
    assert is_delimiter_card(mixed) is False


def test_threshold_boundary():
    # 50% green — should be detected (above 40% threshold)
    half_green = np.zeros((100, 100, 3), dtype=np.uint8)
    half_green[:50, :] = [0, 255, 0]
    assert is_delimiter_card(half_green) is True
