"""Tests for the purse_fixtures pytest fixture (conftest.py)."""
from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image


def test_purse_fixture_returns_path(purse_fixtures):
    """purse_fixtures('tan-tote') should return an existing .png Path."""
    path = purse_fixtures("tan-tote")
    assert isinstance(path, Path)
    assert path.exists(), f"Fixture file not found: {path}"
    assert path.suffix == ".png"


def test_purse_fixture_is_valid_png(purse_fixtures):
    """The resolved path should open as an 800×800 RGBA PNG."""
    path = purse_fixtures("tan-tote")
    img = Image.open(path)
    assert img.format == "PNG"
    assert img.size == (800, 800)


def test_purse_fixture_missing_name_raises(purse_fixtures):
    """Requesting a non-existent fixture should raise FileNotFoundError."""
    with pytest.raises(FileNotFoundError, match="purse fixture"):
        purse_fixtures("nonexistent-bag")
