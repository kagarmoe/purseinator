from __future__ import annotations

import cv2
import numpy as np

# Neon green in HSV: H=35-85, S>100, V>100
GREEN_LOWER = np.array([35, 100, 100])
GREEN_UPPER = np.array([85, 255, 255])
CARD_THRESHOLD = 0.4  # 40% of pixels must be green


def is_delimiter_card(image: np.ndarray) -> bool:
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, GREEN_LOWER, GREEN_UPPER)
    green_ratio = np.count_nonzero(mask) / mask.size
    return green_ratio > CARD_THRESHOLD
