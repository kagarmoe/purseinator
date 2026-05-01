# Purseinator MVP Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a web app where an operator (Kimberly) ingests and enriches handbag photos via CLI, and a curator (Rachel) ranks them through touch-friendly pairwise comparisons to identify keepers vs. sellers.

**Architecture:** FastAPI backend serving a React frontend as a single deployed service. PostgreSQL for data. Operator CLI communicates with the server via REST API. GPU enrichment runs locally on operator's machine. Photos stored on server filesystem with storage keys.

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy (async), Alembic, React, TypeScript, PostgreSQL, Typer (CLI), OpenCV, PyTorch, OpenTelemetry, pytest, Vitest.

**Style:** Functional where possible — pure functions for business logic, frozen Pydantic models, OOP only where frameworks demand it.

---

## Task 1: Project Scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `purseinator/__init__.py`
- Create: `purseinator/main.py`
- Create: `purseinator/config.py`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`
- Create: `.gitignore`
- Create: `alembic.ini`
- Create: `alembic/env.py`
- Create: `frontend/package.json`
- Create: `frontend/tsconfig.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/App.tsx`
- Create: `frontend/index.html`

**Step 1: Create Python project with pyproject.toml**

```toml
[project]
name = "purseinator"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.110",
    "uvicorn[standard]>=0.29",
    "sqlalchemy[asyncio]>=2.0",
    "asyncpg>=0.29",
    "alembic>=1.13",
    "pydantic>=2.6",
    "pydantic-settings>=2.2",
    "typer>=0.12",
    "python-multipart>=0.0.9",
    "opentelemetry-api>=1.24",
    "opentelemetry-sdk>=1.24",
    "opentelemetry-instrumentation-fastapi>=0.45b0",
]

[project.optional-dependencies]
dev = ["pytest>=8.1", "pytest-asyncio>=0.23", "httpx>=0.27"]
gpu = ["torch>=2.2", "opencv-python>=4.9", "pillow>=10.2"]

[project.scripts]
purseinator = "app.cli:app"
```

**Step 2: Create .gitignore**

Standard Python + Node gitignore: `__pycache__`, `.venv`, `node_modules`, `dist`, `.env`, `*.pyc`, `alembic/versions/*.pyc`.

**Step 3: Create purseinator/config.py**

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://localhost:5432/purseinator"
    photo_storage_root: str = "./photos"
    secret_key: str = "change-me-in-production"
    magic_link_expiry_minutes: int = 15
    session_expiry_days: int = 30
    
    model_config = {"env_prefix": "PURSEINATOR_"}

def get_settings() -> Settings:
    return Settings()
```

**Step 4: Create purseinator/main.py with minimal FastAPI app**

```python
from fastapi import FastAPI

def create_app() -> FastAPI:
    app = FastAPI(title="Purseinator", version="0.1.0")

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok"}

    return app

app = create_app()
```

**Step 5: Create tests/conftest.py with async test client**

```python
import pytest
from httpx import ASGITransport, AsyncClient
from app.main import create_app

@pytest.fixture
def app():
    return create_app()

@pytest.fixture
async def client(app):
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as c:
        yield c
```

**Step 6: Write and run a health check test**

```python
# tests/test_health.py
import pytest

@pytest.mark.asyncio
async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
```

Run: `cd /Users/kimberlygarmoe/repos/purseinator && python -m pytest tests/test_health.py -v`
Expected: PASS

**Step 7: Scaffold React frontend with Vite**

Run: `cd /Users/kimberlygarmoe/repos/purseinator && npm create vite@latest frontend -- --template react-ts`

Create a minimal `App.tsx` that renders "Purseinator" text.

**Step 8: Commit**

```bash
git add pyproject.toml purseinator/ tests/ .gitignore alembic.ini alembic/ frontend/
git commit -m "feat: scaffold project — FastAPI backend, React frontend, test infrastructure"
```

---

## Task 2: Database Schema & Models

**Files:**
- Create: `purseinator/models.py`
- Create: `purseinator/database.py`
- Create: `alembic/env.py` (update)
- Create: `alembic/versions/001_initial_schema.py`
- Create: `tests/test_models.py`

**Step 1: Write tests for Pydantic models**

```python
# tests/test_models.py
import pytest
from app.models import UserCreate, ItemCreate, ComparisonCreate

def test_user_create_valid():
    user = UserCreate(email="rachel@example.com", name="Rachel", role="curator")
    assert user.role == "curator"

def test_user_create_invalid_role():
    with pytest.raises(ValueError):
        UserCreate(email="x@x.com", name="X", role="admin")

def test_item_create_unknown_brand():
    item = ItemCreate(collection_id=1, brand="unknown")
    assert item.brand == "unknown"

def test_comparison_create():
    comp = ComparisonCreate(
        collection_id=1, user_id=1,
        item_a_id=1, item_b_id=2, winner_id=1,
        info_level_shown="photos_only",
    )
    assert comp.winner_id in (comp.item_a_id, comp.item_b_id)
```

Run: `python -m pytest tests/test_models.py -v`
Expected: FAIL — models don't exist yet

**Step 2: Create purseinator/models.py with Pydantic schemas + SQLAlchemy tables**

Pydantic models (frozen, for API layer):
- `UserCreate`, `UserRead` — email, name, role (operator|curator)
- `CollectionCreate`, `CollectionRead` — name, description, dollar_goal (nullable)
- `ItemCreate`, `ItemRead` — collection_id, brand, description, condition_score, status
- `ItemPhotoRead` — item_id, storage_key, is_hero, sort_order
- `ComparisonCreate`, `ComparisonRead` — collection_id, user_id, item_a_id, item_b_id, winner_id, info_level_shown, timestamp
- `EloRatingRead` — item_id, collection_id, user_id, rating, comparison_count
- `PriceEstimateRead` — item_id, source, estimated_value, comps_data, fetched_at

SQLAlchemy table definitions (declarative base):
- All 7 tables from the design doc
- Proper foreign keys, indexes on collection_id, user_id
- `info_level_shown` as an enum: photos_only, brand, condition, price

**Step 3: Create purseinator/database.py**

```python
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.config import get_settings

def get_engine():
    return create_async_engine(get_settings().database_url)

def get_session_factory(engine=None):
    engine = engine or get_engine()
    return async_sessionmaker(engine, expire_on_commit=False)
```

**Step 4: Configure Alembic for async and generate initial migration**

Run: `alembic revision --autogenerate -m "initial schema"`
Verify the migration creates all 7 tables.

**Step 5: Run tests**

Run: `python -m pytest tests/test_models.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add purseinator/models.py purseinator/database.py alembic/ tests/test_models.py
git commit -m "feat: database schema — all 7 tables with Pydantic models and initial migration"
```

---

## Task 3: Auth — Magic Link + Persistent Sessions

**Files:**
- Create: `purseinator/auth.py`
- Create: `purseinator/routes/auth.py`
- Create: `tests/test_auth.py`

**Step 1: Write failing tests**

```python
# tests/test_auth.py
import pytest

@pytest.mark.asyncio
async def test_request_magic_link(client):
    resp = await client.post("/auth/magic-link", json={"email": "rachel@example.com"})
    assert resp.status_code == 200

@pytest.mark.asyncio
async def test_verify_magic_link_valid_token(client):
    # Request link, extract token, verify
    resp = await client.post("/auth/magic-link", json={"email": "rachel@example.com"})
    token = resp.json()["token"]  # In prod this goes via email; test returns it
    resp = await client.get(f"/auth/verify?token={token}")
    assert resp.status_code == 200
    assert "session_id" in resp.cookies or "session_id" in resp.json()

@pytest.mark.asyncio
async def test_verify_magic_link_expired_token(client):
    resp = await client.get("/auth/verify?token=expired-garbage")
    assert resp.status_code == 401

@pytest.mark.asyncio
async def test_session_persists(client):
    # Login, then access protected endpoint
    resp = await client.post("/auth/magic-link", json={"email": "rachel@example.com"})
    token = resp.json()["token"]
    resp = await client.get(f"/auth/verify?token={token}")
    session_cookie = resp.cookies.get("session_id")
    resp = await client.get("/auth/me", cookies={"session_id": session_cookie})
    assert resp.status_code == 200
    assert resp.json()["email"] == "rachel@example.com"
```

Run: `python -m pytest tests/test_auth.py -v`
Expected: FAIL

**Step 2: Implement purseinator/auth.py**

Pure functions:
- `create_magic_token(email: str, secret: str, expiry_minutes: int) -> str` — JWT or signed token
- `verify_magic_token(token: str, secret: str) -> str | None` — returns email or None
- `create_session_id() -> str` — UUID
- `get_current_user(session_id: str, db) -> UserRead | None` — lookup session in DB

Need a `sessions` table (or add to existing schema): `id, user_id, session_id, created_at, expires_at`.

**Step 3: Implement purseinator/routes/auth.py**

Routes:
- `POST /auth/magic-link` — accepts email, creates token, returns it (in prod: sends email)
- `GET /auth/verify?token=...` — verifies token, creates user if new, creates session, sets long-lived cookie (30 days)
- `GET /auth/me` — returns current user from session cookie
- `POST /auth/logout` — clears session

**Step 4: Wire routes into main.py**

```python
from app.routes import auth
app.include_router(auth.router, prefix="/auth")
```

**Step 5: Run tests**

Run: `python -m pytest tests/test_auth.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add purseinator/auth.py purseinator/routes/ tests/test_auth.py purseinator/main.py
git commit -m "feat: magic link auth with persistent sessions"
```

---

## Task 4: Collection & Item CRUD API

**Files:**
- Create: `purseinator/routes/collections.py`
- Create: `purseinator/routes/items.py`
- Create: `purseinator/services/collections.py`
- Create: `purseinator/services/items.py`
- Create: `tests/test_collections.py`
- Create: `tests/test_items.py`

**Step 1: Write failing tests for collections**

```python
# tests/test_collections.py
@pytest.mark.asyncio
async def test_create_collection(auth_client):
    resp = await auth_client.post("/collections", json={
        "name": "Rachel's Bags", "description": "The big purge"
    })
    assert resp.status_code == 201
    assert resp.json()["name"] == "Rachel's Bags"

@pytest.mark.asyncio
async def test_list_collections(auth_client):
    await auth_client.post("/collections", json={"name": "Bags"})
    resp = await auth_client.get("/collections")
    assert len(resp.json()) == 1
```

**Step 2: Write failing tests for items**

```python
# tests/test_items.py
@pytest.mark.asyncio
async def test_create_item(auth_client, collection_id):
    resp = await auth_client.post(f"/collections/{collection_id}/items", json={
        "brand": "Coach", "status": "undecided"
    })
    assert resp.status_code == 201

@pytest.mark.asyncio
async def test_create_item_unknown_brand(auth_client, collection_id):
    resp = await auth_client.post(f"/collections/{collection_id}/items", json={
        "brand": "unknown"
    })
    assert resp.status_code == 201
    assert resp.json()["brand"] == "unknown"

@pytest.mark.asyncio
async def test_update_item_brand(auth_client, collection_id, item_id):
    resp = await auth_client.patch(f"/collections/{collection_id}/items/{item_id}", json={
        "brand": "Louis Vuitton"
    })
    assert resp.json()["brand"] == "Louis Vuitton"

@pytest.mark.asyncio
async def test_list_items(auth_client, collection_id):
    resp = await auth_client.get(f"/collections/{collection_id}/items")
    assert resp.status_code == 200
```

Run: `python -m pytest tests/test_collections.py tests/test_items.py -v`
Expected: FAIL

**Step 3: Implement services (pure functions)**

```python
# purseinator/services/collections.py
async def create_collection(db, owner_id: int, data: CollectionCreate) -> CollectionRead: ...
async def list_collections(db, owner_id: int) -> list[CollectionRead]: ...
async def get_collection(db, collection_id: int) -> CollectionRead | None: ...
```

```python
# purseinator/services/items.py
async def create_item(db, collection_id: int, data: ItemCreate) -> ItemRead: ...
async def update_item(db, item_id: int, data: ItemUpdate) -> ItemRead: ...
async def list_items(db, collection_id: int) -> list[ItemRead]: ...
async def get_item(db, item_id: int) -> ItemRead | None: ...
```

**Step 4: Implement routes**

- `POST /collections` — create (operator only)
- `GET /collections` — list user's collections
- `GET /collections/{id}` — get one
- `POST /collections/{id}/items` — create item (operator only)
- `GET /collections/{id}/items` — list items
- `PATCH /collections/{id}/items/{item_id}` — update item
- `GET /collections/{id}/items/{item_id}` — get one item

**Step 5: Run tests**

Run: `python -m pytest tests/test_collections.py tests/test_items.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add purseinator/routes/ purseinator/services/ tests/
git commit -m "feat: collection and item CRUD API"
```

---

## Task 5: Photo Upload & Serving

**Files:**
- Create: `purseinator/services/photos.py`
- Create: `purseinator/routes/photos.py`
- Create: `tests/test_photos.py`

**Step 1: Write failing tests**

```python
# tests/test_photos.py
import io

@pytest.mark.asyncio
async def test_upload_photo(auth_client, collection_id, item_id):
    fake_image = io.BytesIO(b"fake-image-data")
    resp = await auth_client.post(
        f"/collections/{collection_id}/items/{item_id}/photos",
        files={"file": ("bag.jpg", fake_image, "image/jpeg")},
    )
    assert resp.status_code == 201
    assert "storage_key" in resp.json()

@pytest.mark.asyncio
async def test_upload_sets_first_as_hero(auth_client, collection_id, item_id):
    fake_image = io.BytesIO(b"fake-image-data")
    resp = await auth_client.post(
        f"/collections/{collection_id}/items/{item_id}/photos",
        files={"file": ("bag.jpg", fake_image, "image/jpeg")},
    )
    assert resp.json()["is_hero"] is True

@pytest.mark.asyncio
async def test_serve_photo(auth_client, collection_id, item_id):
    # Upload then fetch
    fake_image = io.BytesIO(b"fake-image-data")
    await auth_client.post(
        f"/collections/{collection_id}/items/{item_id}/photos",
        files={"file": ("bag.jpg", fake_image, "image/jpeg")},
    )
    resp = await auth_client.get(f"/collections/{collection_id}/items/{item_id}/photos")
    photos = resp.json()
    storage_key = photos[0]["storage_key"]
    resp = await auth_client.get(f"/photos/{storage_key}")
    assert resp.status_code == 200
```

Run: `python -m pytest tests/test_photos.py -v`
Expected: FAIL

**Step 2: Implement photo service**

```python
# purseinator/services/photos.py
from pathlib import Path

def build_storage_key(collection_id: int, item_id: int, filename: str) -> str:
    return f"collections/{collection_id}/items/{item_id}/{filename}"

async def save_photo(storage_root: str, storage_key: str, data: bytes) -> str:
    path = Path(storage_root) / storage_key
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return storage_key

async def create_photo_record(db, item_id: int, storage_key: str, is_hero: bool) -> ItemPhotoRead: ...
async def list_photos(db, item_id: int) -> list[ItemPhotoRead]: ...
```

**Step 3: Implement routes**

- `POST /collections/{id}/items/{item_id}/photos` — multipart upload, operator only
- `GET /collections/{id}/items/{item_id}/photos` — list photo records
- `GET /photos/{storage_key:path}` — serve photo file (FileResponse)

**Step 4: Run tests**

Run: `python -m pytest tests/test_photos.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add purseinator/services/photos.py purseinator/routes/photos.py tests/test_photos.py
git commit -m "feat: photo upload and serving with filesystem storage"
```

---

## Task 6: Elo Ranking Engine

**Files:**
- Create: `purseinator/services/elo.py`
- Create: `purseinator/services/pairing.py`
- Create: `tests/test_elo.py`
- Create: `tests/test_pairing.py`

**Step 1: Write failing tests for Elo calculations**

```python
# tests/test_elo.py
from app.services.elo import calculate_new_ratings, expected_score

def test_expected_score_equal_ratings():
    score = expected_score(1500, 1500)
    assert score == pytest.approx(0.5)

def test_expected_score_higher_rated_favored():
    score = expected_score(1600, 1400)
    assert score > 0.5

def test_calculate_new_ratings_winner_gains():
    winner_new, loser_new = calculate_new_ratings(
        winner_rating=1500, loser_rating=1500,
        k_factor=32,
    )
    assert winner_new > 1500
    assert loser_new < 1500

def test_calculate_new_ratings_sum_preserved():
    winner_new, loser_new = calculate_new_ratings(1500, 1500, k_factor=32)
    assert winner_new + loser_new == pytest.approx(3000)

def test_k_factor_decreases_with_comparisons():
    from app.services.elo import k_factor_for_item
    assert k_factor_for_item(comparison_count=0) == 32
    assert k_factor_for_item(comparison_count=10) < 32
    assert k_factor_for_item(comparison_count=30) < k_factor_for_item(comparison_count=10)
```

Run: `python -m pytest tests/test_elo.py -v`
Expected: FAIL

**Step 2: Implement Elo engine (pure functions)**

```python
# purseinator/services/elo.py
import math

def expected_score(rating_a: float, rating_b: float) -> float:
    return 1.0 / (1.0 + math.pow(10, (rating_b - rating_a) / 400.0))

def k_factor_for_item(comparison_count: int) -> float:
    """K starts at 32, decays toward 16 as item gets more comparisons."""
    return max(16, 32 * math.exp(-comparison_count / 20))

def calculate_new_ratings(
    winner_rating: float, loser_rating: float, k_factor: float,
) -> tuple[float, float]:
    expected_win = expected_score(winner_rating, loser_rating)
    winner_new = winner_rating + k_factor * (1 - expected_win)
    loser_new = loser_rating + k_factor * (0 - (1 - expected_win))
    return winner_new, loser_new
```

**Step 3: Run Elo tests**

Run: `python -m pytest tests/test_elo.py -v`
Expected: PASS

**Step 4: Write failing tests for adaptive pairing**

```python
# tests/test_pairing.py
from app.services.pairing import select_pair, info_level_for_gap

def test_select_pair_prefers_similar_ratings():
    ratings = [
        (1, 1500, 0), (2, 1510, 0), (3, 1200, 0), (4, 1800, 0),
    ]  # (item_id, rating, comparison_count)
    a, b = select_pair(ratings)
    assert {a, b} == {1, 2}  # closest pair

def test_select_pair_avoids_overcompared_items():
    ratings = [
        (1, 1500, 50), (2, 1510, 50), (3, 1490, 2), (4, 1505, 3),
    ]
    a, b = select_pair(ratings)
    assert {a, b} == {3, 4}  # prefer undercompared items

def test_info_level_photos_only():
    assert info_level_for_gap(250) == "photos_only"

def test_info_level_brand():
    assert info_level_for_gap(150) == "brand"

def test_info_level_condition():
    assert info_level_for_gap(75) == "condition"

def test_info_level_price():
    assert info_level_for_gap(30) == "price"
```

Run: `python -m pytest tests/test_pairing.py -v`
Expected: FAIL

**Step 5: Implement pairing logic**

```python
# purseinator/services/pairing.py
import random

def info_level_for_gap(elo_gap: float) -> str:
    if elo_gap > 200:
        return "photos_only"
    if elo_gap > 100:
        return "brand"
    if elo_gap >= 50:
        return "condition"
    return "price"

def select_pair(
    ratings: list[tuple[int, float, int]],
) -> tuple[int, int]:
    """Select a pair for comparison. Prefers similar ratings and undercompared items.
    
    ratings: list of (item_id, elo_rating, comparison_count)
    Returns: (item_a_id, item_b_id)
    """
    # Sort by comparison count (ascending) to prioritize undercompared
    # Then from candidates, pick the closest pair by rating
    sorted_by_count = sorted(ratings, key=lambda r: r[2])
    # Take the least-compared half
    pool_size = max(len(sorted_by_count) // 2, min(10, len(sorted_by_count)))
    pool = sorted_by_count[:pool_size]
    # Sort pool by rating
    pool.sort(key=lambda r: r[1])
    # Find closest adjacent pair
    best_gap = float("inf")
    best_pair = (pool[0][0], pool[1][0])
    for i in range(len(pool) - 1):
        gap = abs(pool[i][1] - pool[i + 1][1])
        if gap < best_gap:
            best_gap = gap
            best_pair = (pool[i][0], pool[i + 1][0])
    return best_pair
```

**Step 6: Run pairing tests**

Run: `python -m pytest tests/test_pairing.py -v`
Expected: PASS

**Step 7: Commit**

```bash
git add purseinator/services/elo.py purseinator/services/pairing.py tests/test_elo.py tests/test_pairing.py
git commit -m "feat: Elo ranking engine with adaptive pairing and info escalation"
```

---

## Task 7: Ranking API Endpoints

**Files:**
- Create: `purseinator/routes/ranking.py`
- Create: `purseinator/services/ranking.py`
- Create: `tests/test_ranking.py`

**Step 1: Write failing tests**

```python
# tests/test_ranking.py
@pytest.mark.asyncio
async def test_get_next_pair(auth_client, collection_with_items):
    collection_id = collection_with_items
    resp = await auth_client.get(f"/collections/{collection_id}/ranking/next")
    assert resp.status_code == 200
    data = resp.json()
    assert "item_a" in data and "item_b" in data
    assert "info_level" in data
    assert data["item_a"]["id"] != data["item_b"]["id"]

@pytest.mark.asyncio
async def test_submit_comparison(auth_client, collection_with_items):
    collection_id = collection_with_items
    pair = await auth_client.get(f"/collections/{collection_id}/ranking/next")
    pair_data = pair.json()
    resp = await auth_client.post(f"/collections/{collection_id}/ranking/compare", json={
        "item_a_id": pair_data["item_a"]["id"],
        "item_b_id": pair_data["item_b"]["id"],
        "winner_id": pair_data["item_a"]["id"],
        "info_level_shown": pair_data["info_level"],
    })
    assert resp.status_code == 201

@pytest.mark.asyncio
async def test_submit_comparison_updates_elo(auth_client, collection_with_items):
    collection_id = collection_with_items
    # Get initial ratings
    items_before = await auth_client.get(f"/collections/{collection_id}/ranking")
    # Do a comparison
    pair = await auth_client.get(f"/collections/{collection_id}/ranking/next")
    pair_data = pair.json()
    await auth_client.post(f"/collections/{collection_id}/ranking/compare", json={
        "item_a_id": pair_data["item_a"]["id"],
        "item_b_id": pair_data["item_b"]["id"],
        "winner_id": pair_data["item_a"]["id"],
        "info_level_shown": pair_data["info_level"],
    })
    # Verify ratings changed
    items_after = await auth_client.get(f"/collections/{collection_id}/ranking")
    assert items_before.json() != items_after.json()

@pytest.mark.asyncio
async def test_get_ranked_list(auth_client, collection_with_items):
    collection_id = collection_with_items
    resp = await auth_client.get(f"/collections/{collection_id}/ranking")
    assert resp.status_code == 200
    items = resp.json()
    # Should be sorted by rating descending
    ratings = [item["rating"] for item in items]
    assert ratings == sorted(ratings, reverse=True)
```

Run: `python -m pytest tests/test_ranking.py -v`
Expected: FAIL

**Step 2: Implement ranking service**

```python
# purseinator/services/ranking.py
async def initialize_ratings(db, collection_id: int, user_id: int) -> None:
    """Create EloRating records (1500) for all items in collection that don't have one."""
    ...

async def get_next_pair(db, collection_id: int, user_id: int) -> dict:
    """Fetch all ratings, use select_pair, return items + info_level."""
    ...

async def record_comparison(db, data: ComparisonCreate) -> None:
    """Save comparison, update both items' Elo ratings."""
    ...

async def get_ranked_items(db, collection_id: int, user_id: int) -> list[dict]:
    """Return items sorted by Elo rating descending, with rating included."""
    ...
```

**Step 3: Implement routes**

- `GET /collections/{id}/ranking/next` — get next pair to compare (includes photos + info level)
- `POST /collections/{id}/ranking/compare` — submit a comparison result
- `GET /collections/{id}/ranking` — get full ranked list (sorted by Elo descending)

**Step 4: Run tests**

Run: `python -m pytest tests/test_ranking.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add purseinator/routes/ranking.py purseinator/services/ranking.py tests/test_ranking.py
git commit -m "feat: ranking API — next pair, submit comparison, ranked list"
```

---

## Task 8: Rachel's Ranking UI (React)

**Files:**
- Create: `frontend/src/pages/RankingSession.tsx`
- Create: `frontend/src/pages/CollectionView.tsx`
- Create: `frontend/src/pages/SessionPicker.tsx`
- Create: `frontend/src/components/ComparisonCard.tsx`
- Create: `frontend/src/components/DividerLine.tsx`
- Create: `frontend/src/hooks/useRanking.ts`
- Create: `frontend/src/hooks/useOfflineQueue.ts`
- Create: `frontend/src/api.ts`
- Test: `frontend/src/__tests__/`

**Step 1: Set up API client**

```typescript
// frontend/src/api.ts
const API_BASE = import.meta.env.VITE_API_URL || "";

export async function getNextPair(collectionId: number) { ... }
export async function submitComparison(collectionId: number, data: ComparisonData) { ... }
export async function getRankedItems(collectionId: number) { ... }
```

**Step 2: Build SessionPicker page**

Simple screen with two big buttons:
- "Quick Session (2 min)"
- "Full Session (5 min)"

Large, high-contrast, thumb-friendly. This is Rachel's entry point.

**Step 3: Build ComparisonCard component**

- Displays two item photos side by side (stacked on mobile)
- Each photo is a large tap target (minimum 120px x 120px)
- Shows additional info based on `info_level`: photos_only → brand → condition → price
- Tap a photo = select winner
- Subtle animation on selection before loading next pair

**Step 4: Build RankingSession page**

- Receives session duration from SessionPicker
- Fetches pairs from API, shows ComparisonCard
- Progress bar showing time remaining or comparisons done
- "Nice work!" screen at session end
- Can quit anytime (button always visible but not intrusive)

**Step 5: Build useOfflineQueue hook**

```typescript
// frontend/src/hooks/useOfflineQueue.ts
// Queue comparisons in localStorage when offline
// Sync queue to API when connection returns
// Uses navigator.onLine + online/offline events
```

**Step 6: Build CollectionView page**

- Shows all items sorted by Elo rating
- Hero photo for each item
- **Movable dividing line** — draggable separator between keepers and sellers
- Items above line labeled "Keepers" (or just a warm color)
- Items below line labeled "Consider selling" (or just a neutral color)
- Dragging the line updates item statuses via API

**Step 7: Build DividerLine component**

- Draggable horizontal line within the ranked list
- Touch-friendly drag handle (large, obvious)
- Visual feedback while dragging
- Persists position to API on drop

**Step 8: Wire up routing in App.tsx**

```typescript
// Routes:
// / → SessionPicker (for Rachel) or Dashboard (for operator)
// /rank/:collectionId → RankingSession
// /collection/:collectionId → CollectionView
```

**Step 9: Test on mobile viewport**

Use browser dev tools to verify:
- Tap targets ≥ 48px (Google's minimum)
- Text readable without zooming
- No horizontal scroll
- Comparison cards work in portrait orientation

**Step 10: Commit**

```bash
git add frontend/
git commit -m "feat: Rachel's ranking UI — session picker, comparison cards, collection view with divider"
```

---

## Task 9: Operator Review Dashboard

**Files:**
- Create: `frontend/src/pages/Dashboard.tsx`
- Create: `frontend/src/pages/ItemReview.tsx`
- Create: `frontend/src/components/PhotoGroupEditor.tsx`

**Step 1: Build Dashboard page**

- List of collections with item counts
- Ranking progress per collection (% of items with sufficient comparisons)
- Quick stats: total items, keepers, sellers, undecided
- Link to item review for each collection

**Step 2: Build ItemReview page**

- Grid view of all items in a collection
- Each item shows: hero photo, brand, condition score, status
- Click to edit: brand (text input), condition (display from ML), status override
- **Split/merge controls** for photo groups:
  - Split: select a photo within a group, split into new item from that photo onward
  - Merge: select two adjacent items, combine their photos into one item

**Step 3: Build PhotoGroupEditor component**

- Shows all photos for an item in order
- Drag to reorder
- Set hero photo (click star icon)
- Split point marker (click between photos to split)

**Step 4: Commit**

```bash
git add frontend/src/pages/Dashboard.tsx frontend/src/pages/ItemReview.tsx frontend/src/components/
git commit -m "feat: operator dashboard — item review, photo group split/merge"
```

---

## Task 10: CLI — Ingest Command

**Files:**
- Create: `purseinator/cli.py`
- Create: `purseinator/ingest/__init__.py`
- Create: `purseinator/ingest/card_detector.py`
- Create: `purseinator/ingest/grouper.py`
- Create: `tests/test_card_detector.py`
- Create: `tests/test_grouper.py`

**Step 1: Write failing tests for card detection**

```python
# tests/test_card_detector.py
import numpy as np
from app.ingest.card_detector import is_delimiter_card

def test_neon_green_card_detected():
    # Create a fake image that is mostly neon green
    green_image = np.zeros((100, 100, 3), dtype=np.uint8)
    green_image[:, :] = [0, 255, 0]  # BGR green
    assert is_delimiter_card(green_image) is True

def test_bag_photo_not_detected():
    # Create a fake image that is mostly brown/neutral
    brown_image = np.zeros((100, 100, 3), dtype=np.uint8)
    brown_image[:, :] = [50, 100, 150]  # BGR brownish
    assert is_delimiter_card(brown_image) is False

def test_partial_green_not_detected():
    # Only 10% green — not a card
    mixed = np.zeros((100, 100, 3), dtype=np.uint8)
    mixed[:10, :] = [0, 255, 0]
    assert is_delimiter_card(mixed) is False
```

Run: `python -m pytest tests/test_card_detector.py -v`
Expected: FAIL

**Step 2: Implement card detector**

```python
# purseinator/ingest/card_detector.py
import cv2
import numpy as np

# Neon green in HSV: H=55-85, S>100, V>100
GREEN_LOWER = np.array([35, 100, 100])
GREEN_UPPER = np.array([85, 255, 255])
CARD_THRESHOLD = 0.4  # 40% of pixels must be green

def is_delimiter_card(image: np.ndarray) -> bool:
    """Detect if an image is a neon green delimiter card."""
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, GREEN_LOWER, GREEN_UPPER)
    green_ratio = np.count_nonzero(mask) / mask.size
    return green_ratio > CARD_THRESHOLD
```

**Step 3: Run card detector tests**

Run: `python -m pytest tests/test_card_detector.py -v`
Expected: PASS

**Step 4: Write failing tests for grouper**

```python
# tests/test_grouper.py
from app.ingest.grouper import group_photos

def test_group_by_card():
    # Simulate: card, photo, photo, card, photo
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

def test_consecutive_cards_empty_group_skipped():
    files = ["IMG_001.jpg", "IMG_002.jpg", "IMG_003.jpg"]
    is_card = [True, True, False]
    groups = group_photos(files, is_card)
    assert len(groups) == 1
    assert groups[0] == ["IMG_003.jpg"]
```

Run: `python -m pytest tests/test_grouper.py -v`
Expected: FAIL

**Step 5: Implement grouper**

```python
# purseinator/ingest/grouper.py

def group_photos(
    filenames: list[str],
    is_card: list[bool],
) -> list[list[str]]:
    """Split a sequence of photos into groups using card delimiters."""
    groups: list[list[str]] = []
    current: list[str] = []
    for filename, card in zip(filenames, is_card):
        if card:
            if current:
                groups.append(current)
                current = []
        else:
            current.append(filename)
    if current:
        groups.append(current)
    return groups
```

**Step 6: Run grouper tests**

Run: `python -m pytest tests/test_grouper.py -v`
Expected: PASS

**Step 7: Implement CLI ingest command**

```python
# purseinator/cli.py
import typer
app = typer.Typer()

@app.command()
def ingest(
    photo_dir: str,
    server_url: str = typer.Option("http://localhost:8000"),
):
    """Ingest photos from SD card dump. Splits on neon green card delimiter."""
    # 1. List all .jpg/.jpeg/.png files in photo_dir, sorted by name/EXIF date
    # 2. Load each image, run is_delimiter_card()
    # 3. group_photos() to split into item groups
    # 4. Print summary: "Found N items (M photos total)"
    # 5. Save groups locally as JSON manifest for push command
    ...
```

**Step 8: Run all tests**

Run: `python -m pytest tests/ -v`
Expected: ALL PASS

**Step 9: Commit**

```bash
git add purseinator/cli.py purseinator/ingest/ tests/test_card_detector.py tests/test_grouper.py
git commit -m "feat: CLI ingest command — neon green card detection and photo grouping"
```

---

## Task 11: CLI — Push Command

**Files:**
- Modify: `purseinator/cli.py`
- Create: `purseinator/cli_client.py`
- Create: `tests/test_cli_push.py`

**Step 1: Write failing tests**

```python
# tests/test_cli_push.py
from unittest.mock import AsyncMock
from app.cli_client import push_collection

@pytest.mark.asyncio
async def test_push_creates_items(mock_api):
    manifest = {
        "collection_name": "Rachel's Bags",
        "groups": [
            {"photos": ["IMG_002.jpg", "IMG_003.jpg"]},
            {"photos": ["IMG_005.jpg"]},
        ],
    }
    result = await push_collection(mock_api, manifest, photo_dir="/photos")
    assert result["items_created"] == 2
    assert result["photos_uploaded"] == 3
```

Run: `python -m pytest tests/test_cli_push.py -v`
Expected: FAIL

**Step 2: Implement CLI client**

```python
# purseinator/cli_client.py
import httpx
from pathlib import Path

async def push_collection(
    client: httpx.AsyncClient,
    manifest: dict,
    photo_dir: str,
) -> dict:
    """Push ingested items + photos to server via REST API."""
    # 1. Create collection (or use existing)
    # 2. For each group in manifest:
    #    a. Create item (brand="unknown")
    #    b. Upload each photo via multipart
    #    c. Show progress (tqdm or typer.progressbar)
    # 3. Return summary
    ...
```

**Step 3: Add push command to CLI**

```python
@app.command()
def push(
    manifest_path: str,
    photo_dir: str,
    server_url: str = typer.Option("http://localhost:8000"),
    api_key: str = typer.Option(..., envvar="PURSEINATOR_API_KEY"),
):
    """Push ingested photos to the Purseinator server."""
    ...
```

**Step 4: Run tests**

Run: `python -m pytest tests/test_cli_push.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add purseinator/cli.py purseinator/cli_client.py tests/test_cli_push.py
git commit -m "feat: CLI push command — batch upload items and photos to server"
```

---

## Task 12: CLI — Enrich Command (GPU Condition Estimation)

**Files:**
- Modify: `purseinator/cli.py`
- Create: `purseinator/enrich/__init__.py`
- Create: `purseinator/enrich/condition.py`
- Create: `tests/test_condition.py`

**Step 1: Write failing tests**

```python
# tests/test_condition.py
import numpy as np
from app.enrich.condition import estimate_condition

def test_estimate_condition_returns_score():
    fake_image = np.zeros((224, 224, 3), dtype=np.uint8)
    result = estimate_condition(fake_image)
    assert "score" in result
    assert 0.0 <= result["score"] <= 1.0
    assert "label" in result
    assert result["label"] in ("excellent", "good", "fair", "poor")

def test_estimate_condition_returns_details():
    fake_image = np.zeros((224, 224, 3), dtype=np.uint8)
    result = estimate_condition(fake_image)
    assert "details" in result  # wear, scratches, staining sub-scores
```

Run: `python -m pytest tests/test_condition.py -v`
Expected: FAIL

**Step 2: Implement condition estimation**

```python
# purseinator/enrich/condition.py
import numpy as np

def score_to_label(score: float) -> str:
    if score >= 0.85:
        return "excellent"
    if score >= 0.65:
        return "good"
    if score >= 0.40:
        return "fair"
    return "poor"

def estimate_condition(image: np.ndarray) -> dict:
    """Estimate handbag condition from photo.
    
    MVP: Uses a pretrained classification model (e.g., ResNet fine-tuned on
    product condition data, or a zero-shot CLIP approach).
    
    Returns: {"score": 0.0-1.0, "label": str, "details": {...}}
    """
    # MVP placeholder — will be replaced with actual model
    # For now, return a default that signals "needs human review"
    return {
        "score": 0.5,
        "label": "fair",
        "details": {
            "wear": 0.5,
            "scratches": 0.5,
            "staining": 0.5,
        },
    }
```

Note: The actual model integration is a separate research task. This placeholder lets the pipeline work end-to-end while the model is being developed. The CLI will flag items as "ML-estimated" vs "human-reviewed" so the operator knows what to check.

**Step 3: Add enrich command to CLI**

```python
@app.command()
def enrich(
    collection_id: int,
    server_url: str = typer.Option("http://localhost:8000"),
    api_key: str = typer.Option(..., envvar="PURSEINATOR_API_KEY"),
):
    """Run GPU condition estimation on all items in a collection."""
    # 1. Fetch items from server
    # 2. Download photos locally (or use cached)
    # 3. Run estimate_condition on hero photo for each item
    # 4. Push condition scores back to server via PATCH
    # 5. Show progress + summary
    ...
```

**Step 4: Run tests**

Run: `python -m pytest tests/test_condition.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add purseinator/cli.py purseinator/enrich/ tests/test_condition.py
git commit -m "feat: CLI enrich command — GPU condition estimation (placeholder model)"
```

---

## Task 13: OpenTelemetry Integration

**Files:**
- Modify: `purseinator/main.py`
- Create: `purseinator/telemetry.py`
- Create: `tests/test_telemetry.py`

**Step 1: Write failing test**

```python
# tests/test_telemetry.py
from app.telemetry import setup_telemetry

def test_setup_telemetry_returns_tracer():
    tracer = setup_telemetry(service_name="purseinator-test", export=False)
    assert tracer is not None
```

Run: `python -m pytest tests/test_telemetry.py -v`
Expected: FAIL

**Step 2: Implement telemetry setup**

```python
# purseinator/telemetry.py
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.resources import Resource
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

def setup_telemetry(service_name: str = "purseinator", export: bool = True):
    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource)
    
    if export:
        # Configure OTLP exporter for Grafana Cloud
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        provider.add_span_processor(
            BatchSpanProcessor(OTLPSpanExporter())
        )
    
    trace.set_tracer_provider(provider)
    return trace.get_tracer(service_name)

def instrument_app(app):
    FastAPIInstrumentor.instrument_app(app)
```

**Step 3: Wire into main.py**

```python
from app.telemetry import setup_telemetry, instrument_app

def create_app() -> FastAPI:
    app = FastAPI(...)
    setup_telemetry()
    instrument_app(app)
    ...
```

**Step 4: Run tests**

Run: `python -m pytest tests/test_telemetry.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add purseinator/telemetry.py purseinator/main.py tests/test_telemetry.py
git commit -m "feat: OpenTelemetry integration with Grafana Cloud export"
```

---

## Task 14: Elo Convergence Simulation

**Files:**
- Create: `simulations/elo_convergence.py`
- Create: `simulations/README.md`

**Step 1: Build simulation**

```python
# simulations/elo_convergence.py
"""
Simulate Elo ranking convergence for collections of various sizes.

Goal: Determine how many comparisons Rachel needs to do for a usable ranking
of 200 items. "Usable" = the top 30% and bottom 30% are stable (same items
stay in those buckets across additional comparisons).

Usage: python simulations/elo_convergence.py --items 200 --sessions 20
"""
import random
from app.services.elo import calculate_new_ratings, k_factor_for_item
from app.services.pairing import select_pair

def simulate(
    num_items: int,
    comparisons_per_session: int,
    num_sessions: int,
) -> dict:
    # 1. Assign each item a "true preference" score (hidden ground truth)
    # 2. Initialize all Elo ratings at 1500
    # 3. For each session:
    #    a. Select pairs using adaptive pairing
    #    b. "Rachel" picks the item with higher true preference (+ noise)
    #    c. Update Elo ratings
    #    d. Measure: Kendall tau correlation between Elo ranking and true ranking
    #    e. Measure: stability of top 30% and bottom 30%
    # 4. Report: sessions needed for 90% stability
    ...

if __name__ == "__main__":
    # Run with default parameters and print results
    ...
```

**Step 2: Run simulation and document results**

Run: `python simulations/elo_convergence.py --items 200 --sessions 30`

Document findings in `simulations/README.md`:
- How many sessions for stable top/bottom 30%
- How many for stable full ranking
- Recommended session count for Rachel
- Charts if useful

**Step 3: Commit**

```bash
git add simulations/
git commit -m "research: Elo convergence simulation for 200-item collections"
```

---

## Task 15: Integration Testing & Polish

**Files:**
- Create: `tests/test_integration.py`
- Modify: `tests/conftest.py`

**Step 1: Write end-to-end integration test**

```python
# tests/test_integration.py
@pytest.mark.asyncio
async def test_full_workflow(client, tmp_path):
    """Test the complete flow: create user → create collection → add items → rank → view results."""
    # 1. Request magic link
    resp = await client.post("/auth/magic-link", json={"email": "rachel@test.com"})
    token = resp.json()["token"]
    
    # 2. Verify and get session
    resp = await client.get(f"/auth/verify?token={token}")
    cookies = resp.cookies
    
    # 3. Create collection (as operator — need operator auth too)
    # ... create collection, add items with photos
    
    # 4. Initialize rankings
    # 5. Get pair, submit comparison, repeat 5 times
    # 6. Get ranked list — verify sorted by rating
    # 7. Verify comparison history is logged
```

**Step 2: Update conftest.py with shared fixtures**

Add fixtures: `auth_client`, `operator_client`, `collection_id`, `collection_with_items`, test database setup/teardown.

**Step 3: Run full test suite**

Run: `python -m pytest tests/ -v --tb=short`
Expected: ALL PASS

**Step 4: Commit**

```bash
git add tests/
git commit -m "test: end-to-end integration test for full ranking workflow"
```

---

## Task Summary

| Task | Component | Estimated Steps |
|------|-----------|----------------|
| 1 | Project Scaffolding | 8 |
| 2 | Database Schema & Models | 6 |
| 3 | Auth — Magic Link + Sessions | 6 |
| 4 | Collection & Item CRUD | 6 |
| 5 | Photo Upload & Serving | 5 |
| 6 | Elo Ranking Engine | 7 |
| 7 | Ranking API Endpoints | 5 |
| 8 | Rachel's Ranking UI (React) | 10 |
| 9 | Operator Review Dashboard | 4 |
| 10 | CLI — Ingest Command | 9 |
| 11 | CLI — Push Command | 5 |
| 12 | CLI — Enrich Command | 5 |
| 13 | OpenTelemetry Integration | 5 |
| 14 | Elo Convergence Simulation | 3 |
| 15 | Integration Testing | 4 |

**Build order:** Tasks 1-7 are sequential (each builds on the previous). Tasks 8-9 (frontend) can start after Task 7. Tasks 10-12 (CLI) can start after Task 5. Task 13 can be done anytime after Task 1. Task 14 can be done anytime after Task 6. Task 15 is last.

**Dependencies:**
```
1 → 2 → 3 → 4 → 5 → 7
                6 → 7
                      → 8, 9 (frontend, parallel)
               5 → 10 → 11 → 12 (CLI, parallel with frontend)
          1 → 13 (independent)
               6 → 14 (independent)
                              15 (after all others)
```
