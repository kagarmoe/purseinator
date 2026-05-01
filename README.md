# Purseinator

A web app for curating handbag collections through pairwise comparisons. An operator photographs and ingests items via CLI; a curator ranks them through short, touch-friendly "this or that" sessions. Keepers emerge naturally from the rankings.

## Vercel Deployment

The app deploys to Vercel with a static React frontend (`dist/`) and a Python serverless function (`api/index.py`).

**Required environment variables** (set in Vercel project settings):

| Variable | Description |
|----------|-------------|
| `PURSEINATOR_DATABASE_URL` | Postgres connection string — use [Neon](https://neon.tech) for serverless compatibility, e.g. `postgresql+asyncpg://user:pass@host/db` |
| `PURSEINATOR_SECRET_KEY` | Secret key for JWT tokens — generate with `python -c "import secrets; print(secrets.token_urlsafe(32))"` |
| `PURSEINATOR_PHOTO_STORAGE_ROOT` | Photo storage directory — on Vercel use `/tmp` (ephemeral) or configure cloud object storage |

**Deploy:**

1. Connect the GitHub repo to Vercel.
2. Set the environment variables above.
3. Vercel runs `cd frontend && npm run build` and serves `dist/`.
4. API requests to `/api/*` route to `api/index.py` (FastAPI serverless function).

Database migrations must be run separately before first use:
```bash
PURSEINATOR_DATABASE_URL=<neon-url> alembic upgrade head
```

## Requirements

- Python 3.10+ (3.13 tested)
- Node.js 18+ (20.x tested; for frontend development)
- SQLite (bundled with Python; PostgreSQL optional for production)

## Development Setup

Clone the repo wherever you keep projects, then run the steps below from the repo root. All later commands assume you're in the repo root unless otherwise noted.

```bash
git clone https://github.com/kagarmoe/purseinator.git
cd purseinator
```

### macOS

Tested on Apple Silicon (arm64) and Intel (x86_64). Uses Homebrew for system deps.

```bash
# 1. System prerequisites (skip what you already have)
brew install python@3.13 node@20

# 2. Backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head

# 3. Frontend
cd frontend
npm install
cd ..
```

**Apple Silicon note:** native modules (rolldown, esbuild) ship arm64 binaries — `npm install` should pick the right one automatically. If you see `Cannot find module './rolldown-binding.darwin-arm64.node'`, run `rm -rf frontend/node_modules frontend/package-lock.json && cd frontend && npm install`.

### Linux

Tested on Debian/Ubuntu and Linux ARM64 (Docker on Apple Silicon). Uses `apt` for system deps; adapt for your distro.

```bash
# 1. System prerequisites
sudo apt update
sudo apt install -y python3 python3-venv python3-pip nodejs npm

# Or, for newer Node (recommended): https://github.com/nvm-sh/nvm
nvm install 20

# 2. Backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head

# 3. Frontend
cd frontend
npm install
cd ..
```

**Linux ARM64 note (e.g., Docker on Apple Silicon):** if `npm install` finishes but `npm run dev` fails with `Cannot find module './rolldown-binding.linux-arm64-gnu.node'`, the platform-specific binary didn't install. Fix with `rm -rf frontend/node_modules frontend/package-lock.json && cd frontend && npm install`.

## Running Locally

Run backend and frontend in two separate terminals, both started from the repo root.

**Terminal 1 — backend:**
```bash
source .venv/bin/activate
purseinator serve
```
Backend listens on http://localhost:8000. API docs at http://localhost:8000/docs.

**Terminal 2 — frontend:**
```bash
cd frontend
npm run dev
```
Frontend listens on http://localhost:5173 and proxies `/auth/*`, `/collections/*`, `/photos/*`, and `/health` to the backend.

Open http://localhost:5173 and click **Dev Login** to create a test session and explore the app end to end.

### Frontend only (no backend)

If you just want to inspect the UI without running the backend:

```bash
cd frontend
npm run dev
```

API calls will fail, but pages and styles render. Useful for design work.

## Running the Server (alternatives)

The CLI is the easiest way:

```bash
purseinator serve                          # defaults to 0.0.0.0:8000
purseinator serve --host 127.0.0.1 --port 3000
```

Or invoke uvicorn directly:

```bash
uvicorn app.main:create_app --factory --port 8000
```

## Configuration

All settings are configured via environment variables with the `PURSEINATOR_` prefix:

| Variable | Default | Description |
|----------|---------|-------------|
| `PURSEINATOR_DATABASE_URL` | `sqlite+aiosqlite:///./purseinator.db` | Database connection string |
| `PURSEINATOR_PHOTO_STORAGE_ROOT` | `./photos` | Directory for uploaded photos |
| `PURSEINATOR_SECRET_KEY` | `change-me-in-production` | Secret key for JWT tokens |
| `PURSEINATOR_MAGIC_LINK_EXPIRY_MINUTES` | `15` | Magic link token lifetime |
| `PURSEINATOR_SESSION_EXPIRY_DAYS` | `30` | Login session lifetime |

For production with PostgreSQL:

```bash
export PURSEINATOR_DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/purseinator
export PURSEINATOR_SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")
```

## Frontend Pages

The React frontend runs on `http://localhost:5173` during development (proxies API calls to port 8000).

| URL | Page | Who |
|-----|------|-----|
| `/` | Home -- choose a collection | Rachel |
| `/session/:collectionId` | Session picker -- 2 or 5 minute session | Rachel |
| `/rank/:collectionId` | Ranking session -- tap to compare bags | Rachel |
| `/collection/:collectionId` | Ranked list with keeper/seller divider | Rachel |
| `/dashboard` | Operator dashboard -- collection overview | Kimberly |
| `/review/:collectionId` | Item review -- edit brands, view status | Kimberly |

## CLI Commands

All CLI commands are available via `purseinator <command>`.

### `purseinator serve`

Start the API server.

```bash
purseinator serve                          # defaults to 0.0.0.0:8000
purseinator serve --host 127.0.0.1 --port 3000
```

### `purseinator ingest`

Scan a directory of photos from an SD card dump. Detects neon green delimiter cards (OpenCV HSV thresholding) and groups photos into items.

```bash
purseinator ingest ./sd_card_photos/
purseinator ingest ./photos/ --output my_manifest.json
```

Outputs a `manifest.json` file listing the photo groups, ready for `push`.

### `purseinator push`

Upload ingested items and photos to the server.

```bash
purseinator push manifest.json \
  --collection-name "Rachel's Bags" \
  --server-url http://localhost:8000 \
  --session-id $PURSEINATOR_SESSION_ID
```

The `--session-id` can also be set via the `PURSEINATOR_SESSION_ID` environment variable. Get a session ID by calling the `/auth/verify` endpoint.

### Typical Operator Workflow

```bash
# 1. Ingest photos from SD card
purseinator ingest ./sd_card_dump/

# 2. Push to server
export PURSEINATOR_SESSION_ID=<your-session-id>
purseinator push manifest.json --collection-name "Rachel's Bags"

# 3. Review items in the browser
open http://localhost:8000/docs   # or use the dashboard at /dashboard
```

## API Endpoints

### Auth
- `POST /auth/magic-link` -- Request a login token
- `GET /auth/verify?token=...` -- Verify token, create session
- `GET /auth/me` -- Current user info
- `POST /auth/logout` -- End session

### Collections
- `POST /collections` -- Create a collection
- `GET /collections` -- List your collections
- `GET /collections/{id}` -- Get a collection

### Items
- `POST /collections/{id}/items` -- Add an item
- `GET /collections/{id}/items` -- List items
- `GET /collections/{id}/items/{item_id}` -- Get an item
- `PATCH /collections/{id}/items/{item_id}` -- Update an item

### Photos
- `POST /collections/{id}/items/{item_id}/photos` -- Upload a photo (first = hero)
- `GET /collections/{id}/items/{item_id}/photos` -- List photos
- `GET /photos/{storage_key}` -- Serve a photo file

### Ranking
- `GET /collections/{id}/ranking/next` -- Get next pair to compare (adaptive)
- `POST /collections/{id}/ranking/compare` -- Submit comparison result
- `GET /collections/{id}/ranking` -- Ranked list sorted by Elo rating

### Health
- `GET /health` -- Health check

## Project Structure

```
app/                 -- Python package (FastAPI app)
  main.py            -- FastAPI app factory
  config.py          -- Settings (env vars)
  models.py          -- SQLAlchemy tables + Pydantic schemas
  database.py        -- Async engine and session factory
  auth.py            -- Magic link token functions
  deps.py            -- Shared FastAPI dependencies
  cli.py             -- Typer CLI (serve, ingest, push)
  cli_client.py      -- Push client (uploads items + photos)
  telemetry.py       -- OpenTelemetry setup
  routes/            -- API route handlers
  services/          -- Business logic (Elo engine, pairing, ranking)
  ingest/            -- Photo ingestion (card detection, grouping)
  enrich/            -- Condition estimation (GPU, placeholder)
frontend/
  src/pages/         -- React pages (Home, SessionPicker, RankingSession, etc.)
  src/components/    -- Reusable components (ComparisonCard)
  src/api.ts         -- API client
  playwright/        -- Playwright E2E tests (29 tests, full-stack, no mocks)
api/index.py         -- Vercel serverless entry point
alembic/             -- Database migrations
simulations/         -- Elo convergence simulation
tests/               -- pytest test suite (89 tests + 17 GPU-skipped)
docs/                -- Design and implementation docs
```

## Testing

### Backend (pytest)

```bash
# Run all tests
python -m pytest tests/ -v

# Run a specific test file
python -m pytest tests/test_auth.py -v

# Run integration tests only
python -m pytest tests/test_integration.py -v
```

Tests use an in-memory SQLite database and temporary directories for photo storage. No external services needed. 17 tests skip when numpy isn't installed (GPU/condition-detection features); install with `pip install -e ".[gpu]"` to run them.

### Frontend (Playwright E2E)

End-to-end tests run a real backend (FastAPI on port 8000), a real Vite dev server (port 5173), and a real SQLite test DB. No mocking. Tests cover auth, collection management, ranking sessions, timer expiry, collection view, and item review.

```bash
cd frontend
npm test           # runs all 29 E2E tests headless
npm run test:ui    # opens the Playwright UI for debugging
```

The test runner is fully self-contained: it starts the backend, seeds 10 items, runs the suite, and tears everything down.

## Elo Convergence Simulation

Simulate how many comparisons Rachel needs for a usable ranking:

```bash
python -m simulations.elo_convergence --items 200 --sessions 20
```

For 200 items, ~1000 comparisons (about 10 sessions of 100) reaches 0.80+ Kendall tau correlation with the true ranking.

## GPU Features (optional)

For condition estimation on a machine with a GPU:

```bash
pip install -e ".[gpu]"
```
