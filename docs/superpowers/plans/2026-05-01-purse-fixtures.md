# Purse Test Fixtures Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Pre-generate and commit a set of purse-silhouette PNGs as test fixtures, with loader fixtures for pytest and Playwright.
**Architecture:** One-time Pillow generator script writes PNGs to `tests/fixtures/purses/`. Loader fixtures provide `Path` objects (pytest) and upload helpers (Playwright). No runtime image generation in tests.
**Tech Stack:** Python 3.10+, Pillow

---

## Context

- Repo: `/gt/purseinator/crew/kagarmoe/`
- Python package: `app/`
- Tests: `tests/`, conftest at `tests/conftest.py`
- Frontend Playwright: `frontend/playwright/`
- Existing baseline: 107 backend tests + 17 GPU-skipped passing
- Fixture storage layout: `tests/fixtures/purses/{slug}.png` (e.g. `tan-tote`, `black-satchel`, `red-clutch`)
- Size budget: ~200 KB total (~10 KB per PNG), hard cap 250 KB committed

## Why committed fixtures instead of runtime generation

Generating images at test runtime burns CPU on every test run. Committing pre-generated fixtures is CI-friendly and keeps test runs fast. The generator script is run once (or when styles change), and the resulting PNGs are committed. The generator must be deterministic so re-runs produce bit-identical output.

---

## Task 1: Generator script + first fixture

- [ ] Write unit test `tests/test_purse_generator.py` FIRST:
  - Import `make_purse` from `scripts/generate_purse_fixtures`
  - Call `make_purse("tan", "tote")` — no file I/O
  - Assert image size is `(800, 800)`
  - Assert image mode is `"RGBA"`
  - Assert at least one pixel has alpha > 0 (image is non-empty)
  - Test should FAIL at this point (no script yet)
- [ ] Create `scripts/generate_purse_fixtures.py`:
  - `make_purse(color: str, style: str, size: tuple[int, int] = (800, 800)) -> PIL.Image.Image`
    - Returns an RGBA image with transparent background
    - Color palette (approximate hex values, no random variation):
      - `"red"` → `#C0392B`
      - `"brown"` → `#6E2C00`
      - `"tan"` → `#C8A882`
      - `"black"` → `#1C1C1C`
      - `"green"` → `#1E6E3A`
      - `"blue"` → `#1A4A7A`
    - Style shapes (Pillow primitives only — rectangles, ellipses, lines, polygons):
      - `"tote"` — tall rectangle with slightly rounded top corners
      - `"satchel"` — rectangle with arched flap overlay at top
      - `"clutch"` — low wide rectangle (aspect ~2:1)
      - `"hobo"` — rounded bottom (ellipse-clipped rectangle)
      - `"backpack"` — square body with two short parallel rectangles at top for straps
    - Handle: thin arc/line at top center
    - Clasp: small filled rectangle or circle on the body front
    - All drawing coordinates derived from `size` — no hardcoded pixel magic
    - **No random calls anywhere** — fully deterministic
  - `main()`:
    - `argparse` with `--out` (default `tests/fixtures/purses/`) and `--matrix` flag
    - `--matrix` generates the curated 20-pair set (see matrix below) and writes `{color}-{style}.png` files
    - Without `--matrix`, `--color` and `--style` flags generate a single file for ad-hoc use
  - Curated 20-pair matrix (color × style sampling, no duplication):

    | slug | color | style |
    |---|---|---|
    | `tan-tote` | tan | tote |
    | `black-tote` | black | tote |
    | `red-tote` | red | tote |
    | `brown-tote` | brown | tote |
    | `tan-satchel` | tan | satchel |
    | `black-satchel` | black | satchel |
    | `red-satchel` | red | satchel |
    | `green-satchel` | green | satchel |
    | `blue-satchel` | blue | satchel |
    | `tan-clutch` | tan | clutch |
    | `black-clutch` | black | clutch |
    | `red-clutch` | red | clutch |
    | `brown-clutch` | brown | clutch |
    | `blue-clutch` | blue | clutch |
    | `tan-hobo` | tan | hobo |
    | `black-hobo` | black | hobo |
    | `green-hobo` | green | hobo |
    | `tan-backpack` | tan | backpack |
    | `black-backpack` | black | backpack |
    | `blue-backpack` | blue | backpack |

- [ ] Run unit test — it should pass now
- [ ] Run `python scripts/generate_purse_fixtures.py --color tan --style tote --out tests/fixtures/purses/` to produce `tan-tote.png` as proof
- [ ] Commit: `scripts/generate_purse_fixtures.py`, `tests/test_purse_generator.py`, `tests/fixtures/purses/tan-tote.png`

---

## Task 2: Generate full matrix

- [ ] Run `python scripts/generate_purse_fixtures.py --matrix --out tests/fixtures/purses/`
- [ ] Verify total byte count: `du -sh tests/fixtures/purses/` — must be < 250 KB
- [ ] Manually open 3–5 PNGs to confirm they look like recognizable purse silhouettes (not blank or corrupted)
- [ ] Confirm all 20 slugs from the matrix table are present
- [ ] Commit all 20 PNGs in a single commit; include the `du` output in the commit message body (e.g. `Fixtures total: 184 KB`)

---

## Task 3: pytest loader fixture

- [ ] Write test FIRST — add to `tests/test_purse_fixtures.py` (or append to existing conftest test file):
  - Import `purse_fixtures` fixture
  - Call `purse_fixtures("tan-tote")` and assert the returned path exists and ends with `.png`
  - Open the file with Pillow and assert `img.format == "PNG"` and `img.size == (800, 800)`
  - Test should FAIL at this point (fixture not yet defined)
- [ ] Add to `tests/conftest.py`:
  ```python
  @pytest.fixture
  def purse_fixtures():
      """Returns a callable that resolves a fixture name to its Path."""
      base = Path(__file__).parent / "fixtures" / "purses"
      def _get(name: str) -> Path:
          path = base / f"{name}.png"
          if not path.exists():
              raise FileNotFoundError(f"purse fixture {name!r} not found at {path}")
          return path
      return _get
  ```
  - Add `from pathlib import Path` import if not already present
- [ ] Run the new test — it should pass
- [ ] Run full test suite to confirm no regressions (baseline: 107 passing)
- [ ] Commit: updated `tests/conftest.py` + `tests/test_purse_fixtures.py`

---

## Task 4: Playwright helper

- [ ] Write Playwright test FIRST — add a test in `frontend/playwright/` (new file `fixtures.spec.ts` or append to an existing spec):
  - Import `purseFixturePath` from `../fixtures/purse-fixtures`
  - Call `purseFixturePath("tan-tote")` and assert the returned string ends with `tan-tote.png`
  - Use Node `fs.existsSync` to assert the file exists on disk
  - Test should FAIL at this point (helper not yet created)
- [ ] Create `frontend/playwright/fixtures/purse-fixtures.ts`:
  ```typescript
  import { fileURLToPath } from "node:url";
  import { dirname, resolve } from "node:path";

  const __dirname = dirname(fileURLToPath(import.meta.url));
  const FIXTURES_DIR = resolve(__dirname, "../../../tests/fixtures/purses");

  export function purseFixturePath(name: string): string {
    return resolve(FIXTURES_DIR, `${name}.png`);
  }

  export const KNOWN_PURSES = [
    "tan-tote", "black-tote", "red-tote", "brown-tote",
    "tan-satchel", "black-satchel", "red-satchel", "green-satchel", "blue-satchel",
    "tan-clutch", "black-clutch", "red-clutch", "brown-clutch", "blue-clutch",
    "tan-hobo", "black-hobo", "green-hobo",
    "tan-backpack", "black-backpack", "blue-backpack",
  ] as const;

  export type PurseName = typeof KNOWN_PURSES[number];
  ```
- [ ] Run the Playwright test — it should pass
- [ ] Run the full Playwright suite to confirm no regressions
- [ ] Commit: `frontend/playwright/fixtures/purse-fixtures.ts` + the spec file

---

## Task 5: README + regeneration note

- [ ] Add a section to `tests/fixtures/purses/README.md` (create if absent):
  ```
  # Purse test fixtures

  The PNG files in this directory are committed pre-generated test fixtures.
  They are used by pytest (via `purse_fixtures` fixture in `conftest.py`)
  and Playwright (via `purseFixturePath` in `frontend/playwright/fixtures/purse-fixtures.ts`).

  ## Regenerating

  The generator is deterministic. Re-running produces bit-identical output
  unless you intentionally change colors or styles.

      python scripts/generate_purse_fixtures.py --matrix --out tests/fixtures/purses/

  Only re-commit if you intentionally change the color palette, style shapes, or matrix.

  ## Size budget

  Target: ~200 KB total (20 PNGs × ~10 KB each). Hard cap: 250 KB.
  Check current size with: du -sh tests/fixtures/purses/
  ```
- [ ] Commit: `tests/fixtures/purses/README.md`

---

## Self-review checklist

- [ ] **Spec coverage:** generator script (Task 1), fixtures committed (Task 2), pytest loader (Task 3), Playwright helper (Task 4), README (Task 5) — all 5 requirements covered? Yes.
- [ ] **Total fixture bytes documented** in Task 2 commit message? Yes (du output required).
- [ ] **Generator deterministic?** No `random` calls; all coordinates derived from `size` parameter; fixed hex colors. Yes.
- [ ] **No ML dependencies?** Pillow primitives only (rectangles, ellipses, lines, polygons). Yes.
- [ ] **Size under 250 KB?** Verified by `du` in Task 2. Yes.
- [ ] **All 20 slugs present?** Matrix table has exactly 20 entries. Yes.
- [ ] **Baseline preserved?** Full pytest suite run in Task 3; full Playwright suite in Task 4. Yes.
- [ ] **One commit per task?** Yes — 5 commits total.
