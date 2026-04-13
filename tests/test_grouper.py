from __future__ import annotations

from bagfolio.ingest.grouper import group_photos


def test_group_by_card():
    files = ["IMG_001.jpg", "IMG_002.jpg", "IMG_003.jpg", "IMG_004.jpg", "IMG_005.jpg"]
    is_card = [True, False, False, True, False]
    groups = group_photos(files, is_card)
    assert len(groups) == 2
    assert groups[0] == ["IMG_002.jpg", "IMG_003.jpg"]
    assert groups[1] == ["IMG_005.jpg"]


def test_no_cards_single_group():
    files = ["IMG_001.jpg", "IMG_002.jpg"]
    is_card = [False, False]
    groups = group_photos(files, is_card)
    assert len(groups) == 1
    assert groups[0] == ["IMG_001.jpg", "IMG_002.jpg"]


def test_consecutive_cards_empty_group_skipped():
    files = ["IMG_001.jpg", "IMG_002.jpg", "IMG_003.jpg"]
    is_card = [True, True, False]
    groups = group_photos(files, is_card)
    assert len(groups) == 1
    assert groups[0] == ["IMG_003.jpg"]


def test_all_cards_no_groups():
    files = ["IMG_001.jpg", "IMG_002.jpg"]
    is_card = [True, True]
    groups = group_photos(files, is_card)
    assert len(groups) == 0


def test_empty_input():
    groups = group_photos([], [])
    assert len(groups) == 0
