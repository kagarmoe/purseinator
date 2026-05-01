"""
Deterministic purse-silhouette PNG generator for test fixtures.

Generates stylised purse silhouettes using Pillow primitives only.
No random calls — all coordinates derived from the requested image size.
Re-running produces bit-identical output.

Usage
-----
# Single image (ad-hoc):
    python scripts/generate_purse_fixtures.py --color tan --style tote --out tests/fixtures/purses/

# Full matrix (20 images):
    python scripts/generate_purse_fixtures.py --matrix --out tests/fixtures/purses/
"""
from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw

# ---------------------------------------------------------------------------
# Fixed colour palette — no random variation
# ---------------------------------------------------------------------------
PALETTE: dict[str, tuple[int, int, int]] = {
    "red":    (0xC0, 0x39, 0x2B),
    "brown":  (0x6E, 0x2C, 0x00),
    "tan":    (0xC8, 0xA8, 0x82),
    "black":  (0x1C, 0x1C, 0x1C),
    "green":  (0x1E, 0x6E, 0x3A),
    "blue":   (0x1A, 0x4A, 0x7A),
}

# Slightly lighter version of the body colour used for the flap/detail
def _lighten(rgb: tuple[int, int, int], amount: int = 40) -> tuple[int, int, int]:
    return tuple(min(255, c + amount) for c in rgb)  # type: ignore[return-value]

def _darken(rgb: tuple[int, int, int], amount: int = 30) -> tuple[int, int, int]:
    return tuple(max(0, c - amount) for c in rgb)  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Drawing helpers (all coords derived from w, h)
# ---------------------------------------------------------------------------

def _draw_handle(draw: ImageDraw.ImageDraw, cx: int, top_y: int, w: int, h: int,
                 fill: tuple[int, int, int]) -> None:
    """Draw a simple arc handle centred above the body."""
    hw = w // 6          # half-handle width
    hh = h // 10         # handle height
    lw = max(4, w // 60) # line width
    bbox = [cx - hw, top_y - hh, cx + hw, top_y + hh // 2]
    draw.arc(bbox, start=200, end=340, fill=fill, width=lw)


def _draw_clasp(draw: ImageDraw.ImageDraw, cx: int, y: int, w: int,
                fill: tuple[int, int, int]) -> None:
    """Small rectangular clasp centred on the body."""
    cw = w // 20
    ch = w // 28
    draw.rectangle([cx - cw, y - ch, cx + cw, y + ch], fill=fill)


def _rgba(rgb: tuple[int, int, int], a: int = 255) -> tuple[int, int, int, int]:
    return (rgb[0], rgb[1], rgb[2], a)


# ---------------------------------------------------------------------------
# Style drawing functions — each receives an ImageDraw and dimension params
# ---------------------------------------------------------------------------

def _draw_tote(draw: ImageDraw.ImageDraw, w: int, h: int,
               body_color: tuple[int, int, int]) -> None:
    """Tall rectangle with slightly inset top corners (tote bag)."""
    margin = w // 8
    top = h // 4
    bottom = h - h // 8

    # Body — plain filled rectangle
    draw.rectangle([margin, top, w - margin, bottom], fill=_rgba(body_color))

    # Slight rounded effect: small triangles cut from top corners
    corner = w // 20
    draw.polygon([
        (margin, top),
        (margin + corner, top),
        (margin, top + corner),
    ], fill=(0, 0, 0, 0))
    draw.polygon([
        (w - margin, top),
        (w - margin - corner, top),
        (w - margin, top + corner),
    ], fill=(0, 0, 0, 0))

    # Straps: two parallel rectangles symmetrically placed
    strap_w = w // 16
    strap_h = top
    strap_gap = w // 10
    for ox in [cx := w // 2 - strap_gap // 2 - strap_w, cx + strap_gap]:
        draw.rectangle([ox, 0, ox + strap_w, strap_h], fill=_rgba(_darken(body_color)))

    # Clasp
    clasp_color = _rgba(_lighten(body_color, 60))
    _draw_clasp(draw, w // 2, (top + bottom) // 2, w, clasp_color)


def _draw_satchel(draw: ImageDraw.ImageDraw, w: int, h: int,
                  body_color: tuple[int, int, int]) -> None:
    """Rectangle body with arched flap overlay at top."""
    margin = w // 8
    body_top = h // 3
    bottom = h - h // 8

    # Body
    draw.rectangle([margin, body_top, w - margin, bottom], fill=_rgba(body_color))

    # Flap — slightly lighter trapezoid covering upper third of body
    flap_bottom = body_top + (bottom - body_top) // 3
    flap_color = _rgba(_lighten(body_color, 30))
    draw.rectangle([margin, body_top, w - margin, flap_bottom], fill=flap_color)

    # Arched top of flap using a filled ellipse clipped to the flap area
    arch_h = (bottom - body_top) // 5
    draw.ellipse([margin, body_top - arch_h, w - margin, body_top + arch_h],
                 fill=flap_color)

    # Single shoulder strap
    strap_w = w // 14
    cx = w // 2
    draw.rectangle([cx - strap_w // 2, 0, cx + strap_w // 2, body_top],
                   fill=_rgba(_darken(body_color)))

    # Clasp
    _draw_clasp(draw, w // 2, flap_bottom, w, _rgba(_lighten(body_color, 70)))


def _draw_clutch(draw: ImageDraw.ImageDraw, w: int, h: int,
                 body_color: tuple[int, int, int]) -> None:
    """Low wide rectangle (aspect ~2:1)."""
    margin_x = w // 10
    margin_y = h // 3
    bottom = h - h // 3

    draw.rectangle([margin_x, margin_y, w - margin_x, bottom], fill=_rgba(body_color))

    # Dividing seam line roughly 40% from left
    seam_x = margin_x + (w - 2 * margin_x) * 4 // 10
    draw.line([(seam_x, margin_y), (seam_x, bottom)],
              fill=_rgba(_darken(body_color, 40)), width=max(2, w // 80))

    # Clasp on left panel centre
    cx_clasp = (margin_x + seam_x) // 2
    cy_clasp = (margin_y + bottom) // 2
    _draw_clasp(draw, cx_clasp, cy_clasp, w, _rgba(_lighten(body_color, 60)))


def _draw_hobo(draw: ImageDraw.ImageDraw, w: int, h: int,
               body_color: tuple[int, int, int]) -> None:
    """Rounded bottom bag — square body with elliptical lower half."""
    margin = w // 8
    top = h // 5
    mid = h // 2
    bottom = h - h // 10

    # Upper rectangle
    draw.rectangle([margin, top, w - margin, mid], fill=_rgba(body_color))
    # Lower ellipse
    draw.ellipse([margin, mid - (mid - top) // 2, w - margin, bottom],
                 fill=_rgba(body_color))

    # Single arc handle
    _draw_handle(draw, w // 2, top, w, h, _rgba(_darken(body_color)))

    # Clasp
    _draw_clasp(draw, w // 2, mid - (mid - top) // 4, w, _rgba(_lighten(body_color, 60)))


def _draw_backpack(draw: ImageDraw.ImageDraw, w: int, h: int,
                   body_color: tuple[int, int, int]) -> None:
    """Square body with two short parallel rectangles at top for straps."""
    margin = w // 8
    top = h // 5
    bottom = h - h // 8

    # Main body
    draw.rectangle([margin, top, w - margin, bottom], fill=_rgba(body_color))

    # Shoulder straps — two narrow rectangles above the body
    strap_w = w // 14
    strap_h = top
    cx = w // 2
    gap = w // 8
    for strap_x in [cx - gap - strap_w, cx + gap]:
        draw.rectangle([strap_x, 0, strap_x + strap_w, top],
                       fill=_rgba(_darken(body_color)))

    # Front pocket — centred rectangle in lower half
    pocket_margin = w // 5
    pocket_top = top + (bottom - top) * 55 // 100
    pocket_bot = bottom - (bottom - top) // 10
    pocket_color = _rgba(_darken(body_color, 20))
    draw.rectangle([pocket_margin, pocket_top, w - pocket_margin, pocket_bot],
                   fill=pocket_color)

    # Pocket clasp
    _draw_clasp(draw, w // 2, (pocket_top + pocket_bot) // 2, w,
                _rgba(_lighten(body_color, 60)))

    # Top handle — small rectangle bridge
    h_w = w // 8
    h_h = h // 20
    h_t = max(0, top - h_h - 2)
    draw.rectangle([cx - h_w // 2, h_t, cx + h_w // 2, top],
                   fill=_rgba(_darken(body_color)))


_STYLE_FUNCS = {
    "tote":     _draw_tote,
    "satchel":  _draw_satchel,
    "clutch":   _draw_clutch,
    "hobo":     _draw_hobo,
    "backpack": _draw_backpack,
}

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def make_purse(
    color: str,
    style: str,
    size: tuple[int, int] = (800, 800),
) -> "Image.Image":
    """
    Return an RGBA ``PIL.Image`` silhouette for *color* × *style*.

    Fully deterministic — no random calls.  Re-running with the same arguments
    produces a byte-identical PNG when saved.
    """
    if color not in PALETTE:
        raise ValueError(f"Unknown color {color!r}. Valid: {sorted(PALETTE)}")
    if style not in _STYLE_FUNCS:
        raise ValueError(f"Unknown style {style!r}. Valid: {sorted(_STYLE_FUNCS)}")

    w, h = size
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    _STYLE_FUNCS[style](draw, w, h, PALETTE[color])
    return img


# ---------------------------------------------------------------------------
# Curated 20-pair matrix
# ---------------------------------------------------------------------------
MATRIX: list[tuple[str, str]] = [
    ("tan",   "tote"),
    ("black", "tote"),
    ("red",   "tote"),
    ("brown", "tote"),
    ("tan",   "satchel"),
    ("black", "satchel"),
    ("red",   "satchel"),
    ("green", "satchel"),
    ("blue",  "satchel"),
    ("tan",   "clutch"),
    ("black", "clutch"),
    ("red",   "clutch"),
    ("brown", "clutch"),
    ("blue",  "clutch"),
    ("tan",   "hobo"),
    ("black", "hobo"),
    ("green", "hobo"),
    ("tan",   "backpack"),
    ("black", "backpack"),
    ("blue",  "backpack"),
]


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Generate purse-silhouette PNG fixtures.")
    parser.add_argument("--out", default="tests/fixtures/purses/",
                        help="Output directory (default: tests/fixtures/purses/)")
    parser.add_argument("--matrix", action="store_true",
                        help="Generate the full 20-pair curated matrix.")
    parser.add_argument("--color", help="Single-image: colour name")
    parser.add_argument("--style", help="Single-image: style name")
    args = parser.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.matrix:
        for color, style in MATRIX:
            img = make_purse(color, style)
            out_path = out_dir / f"{color}-{style}.png"
            img.save(out_path, format="PNG")
            print(f"  wrote {out_path}")
        print(f"Done. {len(MATRIX)} images written to {out_dir}")
    else:
        if not args.color or not args.style:
            parser.error("Provide --color and --style for single-image mode, or use --matrix.")
        img = make_purse(args.color, args.style)
        out_path = out_dir / f"{args.color}-{args.style}.png"
        img.save(out_path, format="PNG")
        print(f"  wrote {out_path}")


if __name__ == "__main__":
    main()
