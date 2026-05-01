from __future__ import annotations

import importlib.util

import pytest

from app.ingest.grouper import group_photos

numpy_available = importlib.util.find_spec("numpy") is not None
skip_no_gpu = pytest.mark.skipif(
    not numpy_available,
    reason="requires gpu extras: pip install -e '.[gpu]'"
)


@skip_no_gpu
def test_group_by_card():
    files = ["IMG_001.jpg", "IMG_002.jpg", "IMG_003.jpg", "IMG_004.jpg", "IMG_005.jpg"]
    is_card = [True, False, False, True, False]
    groups = group_photos(files, is_card)
    assert len(groups) == 2
    assert groups[0] == ["IMG_002.jpg", "IMG_003.jpg"]
    assert groups[1] == ["IMG_005.jpg"]


@skip_no_gpu
def test_no_cards_single_group():
    files = ["IMG_001.jpg", "IMG_002.jpg"]
    is_card = [False, False]
    groups = group_photos(files, is_card)
    assert len(groups) == 1
    assert groups[0] == ["IMG_001.jpg", "IMG_002.jpg"]


@skip_no_gpu
def test_consecutive_cards_empty_group_skipped():
    files = ["IMG_001.jpg", "IMG_002.jpg", "IMG_003.jpg"]
    is_card = [True, True, False]
    groups = group_photos(files, is_card)
    assert len(groups) == 1
    assert groups[0] == ["IMG_003.jpg"]


@skip_no_gpu
def test_all_cards_no_groups():
    files = ["IMG_001.jpg", "IMG_002.jpg"]
    is_card = [True, True]
    groups = group_photos(files, is_card)
    assert len(groups) == 0


@skip_no_gpu
def test_empty_input():
    groups = group_photos([], [])
    assert len(groups) == 0
