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
  cli.py           -- Typer CLI
  routes/          -- API route handlers
  services/        -- Business logic (Elo engine, pairing)
alembic/           -- Database migrations
frontend/          -- React + TypeScript + Vite
tests/             -- pytest test suite
docs/plans/        -- Design and implementation docs
```

## Testing

```bash
# Run all tests
python -m pytest tests/ -v

# Run a specific test file
python -m pytest tests/test_auth.py -v
```

Tests use an in-memory SQLite database and temporary directories for photo storage. No external services needed.

## GPU Features (optional)

For condition estimation on a machine with a GPU:

```bash
pip install -e ".[gpu]"
```
