"""Unit tests for the purse fixture generator script."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

# Load the script from scripts/ directory (not a package)
_SCRIPT_PATH = Path(__file__).parent.parent / "scripts" / "generate_purse_fixtures.py"


def _load_generator():
    spec = importlib.util.spec_from_file_location("generate_purse_fixtures", _SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestMakePurse:
    def test_returns_rgba_800x800(self):
        gen = _load_generator()
        img = gen.make_purse("tan", "tote")
        assert img.size == (800, 800)
        assert img.mode == "RGBA"

    def test_image_is_non_empty(self):
        gen = _load_generator()
        img = gen.make_purse("tan", "tote")
        pixels = list(img.getdata())
        # At least one pixel must have alpha > 0
        assert any(p[3] > 0 for p in pixels), "Image appears to be completely transparent"

    def test_all_styles_produce_valid_images(self):
        gen = _load_generator()
        styles = ["tote", "satchel", "clutch", "hobo", "backpack"]
        colors = ["tan", "black", "red", "brown", "green", "blue"]
        for style in styles:
            for color in colors:
                img = gen.make_purse(color, style)
                assert img.size == (800, 800)
                assert img.mode == "RGBA"

    def test_deterministic_output(self):
        """Re-runs must produce byte-identical images."""
        gen = _load_generator()
        import io
        img1 = gen.make_purse("black", "satchel")
        img2 = gen.make_purse("black", "satchel")
        buf1, buf2 = io.BytesIO(), io.BytesIO()
        img1.save(buf1, format="PNG")
        img2.save(buf2, format="PNG")
        assert buf1.getvalue() == buf2.getvalue(), "Generator is not deterministic"
