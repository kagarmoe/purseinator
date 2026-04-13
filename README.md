# Bagfolio

A web app for curating handbag collections through pairwise comparisons. An operator photographs and ingests items via CLI; a curator ranks them through short, touch-friendly "this or that" sessions. Keepers emerge naturally from the rankings.

## Requirements

- Python 3.10+
- Node.js 18+ (for frontend development)

## Development Setup

```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate

# Install the package with dev dependencies
pip install -e ".[dev]"

# Run database migrations (creates local SQLite DB)
alembic upgrade head

# Run tests
python -m pytest tests/ -v
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Running the Server

```bash
# Using the CLI
bagfolio serve

# Or directly with uvicorn
uvicorn bagfolio.main:create_app --factory --port 8000
```

The API docs are at http://localhost:8000/docs once the server is running.

## Configuration

All settings are configured via environment variables with the `BAGFOLIO_` prefix:

| Variable | Default | Description |
|----------|---------|-------------|
| `BAGFOLIO_DATABASE_URL` | `sqlite+aiosqlite:///./bagfolio.db` | Database connection string |
| `BAGFOLIO_PHOTO_STORAGE_ROOT` | `./photos` | Directory for uploaded photos |
| `BAGFOLIO_SECRET_KEY` | `change-me-in-production` | Secret key for JWT tokens |
| `BAGFOLIO_MAGIC_LINK_EXPIRY_MINUTES` | `15` | Magic link token lifetime |
| `BAGFOLIO_SESSION_EXPIRY_DAYS` | `30` | Login session lifetime |

For production with PostgreSQL:

```bash
export BAGFOLIO_DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/bagfolio
export BAGFOLIO_SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")
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

All CLI commands are available via `bagfolio <command>`.

### `bagfolio serve`

Start the API server.

```bash
bagfolio serve                          # defaults to 0.0.0.0:8000
bagfolio serve --host 127.0.0.1 --port 3000
```

### `bagfolio ingest`

Scan a directory of photos from an SD card dump. Detects neon green delimiter cards (OpenCV HSV thresholding) and groups photos into items.

```bash
bagfolio ingest ./sd_card_photos/
bagfolio ingest ./photos/ --output my_manifest.json
```

Outputs a `manifest.json` file listing the photo groups, ready for `push`.

### `bagfolio push`

Upload ingested items and photos to the server.

```bash
bagfolio push manifest.json \
  --collection-name "Rachel's Bags" \
  --server-url http://localhost:8000 \
  --session-id $BAGFOLIO_SESSION_ID
```

The `--session-id` can also be set via the `BAGFOLIO_SESSION_ID` environment variable. Get a session ID by calling the `/auth/verify` endpoint.

### Typical Operator Workflow

```bash
# 1. Ingest photos from SD card
bagfolio ingest ./sd_card_dump/

# 2. Push to server
export BAGFOLIO_SESSION_ID=<your-session-id>
bagfolio push manifest.json --collection-name "Rachel's Bags"

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
bagfolio/
  main.py          -- FastAPI app factory
  config.py        -- Settings (env vars)
  models.py        -- SQLAlchemy tables + Pydantic schemas
  database.py      -- Async engine and session factory
  auth.py          -- Magic link token functions
  deps.py          -- Shared FastAPI dependencies
  cli.py           -- Typer CLI (serve, ingest, push)
  cli_client.py    -- Push client (uploads items + photos)
  telemetry.py     -- OpenTelemetry setup
  routes/          -- API route handlers
  services/        -- Business logic (Elo engine, pairing, ranking)
  ingest/          -- Photo ingestion (card detection, grouping)
  enrich/          -- Condition estimation (GPU, placeholder)
frontend/
  src/pages/       -- React pages (Home, SessionPicker, RankingSession, etc.)
  src/components/  -- Reusable components (ComparisonCard)
  src/api.ts       -- API client
alembic/           -- Database migrations
simulations/       -- Elo convergence simulation
tests/             -- pytest test suite (83 tests)
docs/plans/        -- Design and implementation docs
```

## Testing

```bash
# Run all tests
python -m pytest tests/ -v

# Run a specific test file
python -m pytest tests/test_auth.py -v

# Run integration tests only
python -m pytest tests/test_integration.py -v
```

Tests use an in-memory SQLite database and temporary directories for photo storage. No external services needed.

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
