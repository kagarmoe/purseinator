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

Target: ~200 KB total (20 PNGs x ~10 KB each). Hard cap: 250 KB.
Check current size with: du -sh tests/fixtures/purses/
