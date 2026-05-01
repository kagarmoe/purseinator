# Backend TDD Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fill every gap between the current 70-test baseline and the complete backend spec, using TDD throughout.

**Architecture:** FastAPI + SQLAlchemy async. Tests use an in-memory SQLite DB via conftest fixtures (`db_client`, `auth_client`). Each gap: write failing test → run → fix implementation → run → commit.

**Tech Stack:** Python 3.10+, FastAPI, SQLAlchemy async, pytest-asyncio, httpx ASGITransport, aiosqlite

**Note on status values:** The model uses `"undecided"` (not `"unranked"`). The spec had a typo — use `"undecided"` everywhere.

---

### Task 1: Skip GPU-dependent tests when numpy is absent

**Files:**
- Modify: `tests/test_card_detector.py`
- Modify: `tests/test_condition.py`
- Modify: `tests/test_grouper.py`
- Modify: `tests/test_integration.py`

- [ ] **Step 1: Add skip guard to test_card_detector.py**

Replace the top of `tests/test_card_detector.py`:
```python
from __future__ import annotations
import importlib.util
import pytest

numpy_available = importlib.util.find_spec("numpy") is not None
skip_no_gpu = pytest.mark.skipif(
    not numpy_available,
    reason="requires gpu extras: pip install -e '.[gpu]'"
)
```
Then add `@skip_no_gpu` decorator to every test function in that file.

- [ ] **Step 2: Add skip guard to test_condition.py and test_grouper.py**

Same pattern — add to top of each file:
```python
from __future__ import annotations
import importlib.util
import pytest

numpy_available = importlib.util.find_spec("numpy") is not None
skip_no_gpu = pytest.mark.skipif(
    not numpy_available,
    reason="requires gpu extras: pip install -e '.[gpu]'"
)
```
Add `@skip_no_gpu` to each test function.

- [ ] **Step 3: Fix test_ingest_and_push_workflow in test_integration.py**

Add to top of `tests/test_integration.py`:
```python
import importlib.util
numpy_available = importlib.util.find_spec("numpy") is not None
skip_no_gpu = pytest.mark.skipif(
    not numpy_available,
    reason="requires gpu extras: pip install -e '.[gpu]'"
)
```
Add `@skip_no_gpu` to `test_ingest_and_push_workflow` only.

- [ ] **Step 4: Run tests — all should pass or skip, none should error**

```bash
cd /gt/purseinator/purseinator
python3 -m pytest tests/ -q
```
Expected: 70 passed, 4+ skipped, 0 errors

- [ ] **Step 5: Commit**
```bash
git add tests/test_card_detector.py tests/test_condition.py tests/test_grouper.py tests/test_integration.py
git commit -m "test: skip gpu-dependent tests when numpy is absent"
```

---

### Task 2: Token reuse 401 — add UsedTokenTable and single-use enforcement

**Background:** Magic tokens are stateless JWTs — there is no DB row to "delete". To enforce single-use, we must: add a `jti` (JWT ID) claim to each token, add a `UsedTokenTable` model, add an alembic migration, and check/mark `jti` in the verify endpoint.

**Files:**
- Modify: `purseinator/auth.py`
- Modify: `purseinator/models.py`
- Modify: `purseinator/routes/auth.py`
- Create: `alembic/versions/<rev>_add_used_tokens_table.py`
- Modify: `tests/test_auth.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_auth.py`:
```python
@pytest.mark.asyncio
async def test_verify_token_reuse_returns_401(db_client):
    resp = await db_client.post("/auth/magic-link", json={"email": "rachel@example.com"})
    token = resp.json()["token"]
    # First use — should succeed
    resp1 = await db_client.get(f"/auth/verify?token={token}")
    assert resp1.status_code == 200
    # Second use — must fail
    resp2 = await db_client.get(f"/auth/verify?token={token}")
    assert resp2.status_code == 401
```

- [ ] **Step 2: Run to confirm it fails**

```bash
python3 -m pytest tests/test_auth.py::test_verify_token_reuse_returns_401 -v
```
Expected: FAIL — second use returns 200 (token reuse not blocked)

- [ ] **Step 3: Add UsedTokenTable to models.py**

Add after `SessionTable` in `purseinator/models.py`:
```python
class UsedTokenTable(Base):
    __tablename__ = "used_tokens"

    id = Column(Integer, primary_key=True)
    jti = Column(String(255), unique=True, nullable=False, index=True)
    used_at = Column(DateTime, server_default=func.now())
```

- [ ] **Step 4: Add alembic migration**

```bash
cd /gt/purseinator/purseinator
alembic revision --autogenerate -m "add used_tokens table"
```
Verify the generated file in `alembic/versions/` contains `create_table("used_tokens", ...)`.

Run it:
```bash
PURSEINATOR_DATABASE_URL="sqlite+aiosqlite:///./dev.db" alembic upgrade head
```

- [ ] **Step 5: Update auth.py — add jti to token, return (email, jti) from verify**

Replace `purseinator/auth.py` with:
```python
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import jwt


def create_magic_token(email: str, secret: str, expiry_minutes: int = 15) -> str:
    payload = {
        "jti": str(uuid.uuid4()),
        "email": email,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=expiry_minutes),
        "type": "magic_link",
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def verify_magic_token(token: str, secret: str) -> tuple[str, str] | None:
    """Returns (email, jti) or None if invalid/expired."""
    try:
        payload = jwt.decode(token, secret, algorithms=["HS256"])
        if payload.get("type") != "magic_link":
            return None
        email = payload.get("email")
        jti = payload.get("jti")
        if not email or not jti:
            return None
        return email, jti
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None


def create_session_id() -> str:
    return str(uuid.uuid4())
```

- [ ] **Step 6: Update routes/auth.py — check and mark jti used**

Replace the `verify` endpoint in `purseinator/routes/auth.py`:
```python
@router.get("/verify")
async def verify(token: str, db: AsyncSession = Depends(get_db)):
    settings = get_settings()
    result = verify_magic_token(token, settings.secret_key)
    if result is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    email, jti = result

    # Reject reuse
    used = await db.execute(
        select(UsedTokenTable).where(UsedTokenTable.jti == jti)
    )
    if used.scalar_one_or_none() is not None:
        raise HTTPException(status_code=401, detail="Token already used")

    # Find or create user
    user_result = await db.execute(select(UserTable).where(UserTable.email == email))
    user = user_result.scalar_one_or_none()
    if user is None:
        user = UserTable(email=email, name=email.split("@")[0], role="curator")
        db.add(user)
        await db.flush()

    # Mark token used
    db.add(UsedTokenTable(jti=jti))

    sid = create_session_id()
    session = SessionTable(
        session_id=sid,
        user_id=user.id,
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.session_expiry_days),
    )
    db.add(session)
    await db.commit()

    return {"session_id": sid, "email": email}
```

Also add `UsedTokenTable` to the imports at the top of `routes/auth.py`:
```python
from purseinator.models import SessionTable, UsedTokenTable, UserTable
```

- [ ] **Step 7: Run the token reuse test**

```bash
python3 -m pytest tests/test_auth.py::test_verify_token_reuse_returns_401 -v
```
Expected: PASS

- [ ] **Step 8: Add the 422 coverage test and run full auth suite**

Add to `tests/test_auth.py` (coverage — FastAPI validates this automatically):
```python
@pytest.mark.asyncio
async def test_magic_link_missing_email_returns_422(db_client):
    resp = await db_client.post("/auth/magic-link", json={})
    assert resp.status_code == 422
```

Run full suite:
```bash
python3 -m pytest tests/test_auth.py -v
```
Expected: all pass

- [ ] **Step 9: Commit**
```bash
git add purseinator/auth.py purseinator/models.py purseinator/routes/auth.py \
        alembic/versions/ tests/test_auth.py
git commit -m "feat: single-use magic tokens via UsedTokenTable jti tracking"
```

---

### Task 3: Collections — non-owner gets 403

**Background:** `GET /collections/{id}` currently returns 200 for any authenticated user who knows the ID, regardless of ownership. `GET /collections` already scopes by `owner_id` — no fix needed there.

**Files:**
- Modify: `tests/test_collections.py`
- Modify: `purseinator/routes/collections.py`

- [ ] **Step 1: Write the failing test**

Add a second `auth_client` fixture for a different user in `tests/test_collections.py`:
```python
@pytest.fixture
async def other_auth_client(db_engine, db_session_factory, photo_storage_root):
    """A second authenticated client as a different user."""
    app = create_app(session_factory=db_session_factory, photo_storage_root=photo_storage_root)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/auth/magic-link", json={"email": "kimberly@example.com"})
        token = resp.json()["token"]
        resp = await ac.get(f"/auth/verify?token={token}")
        session_id = resp.json()["session_id"]
        ac.cookies.set("session_id", session_id)
        yield ac
```

Add the import at the top of `tests/test_collections.py` if not already present:
```python
from httpx import ASGITransport, AsyncClient
from purseinator.main import create_app
```

Add the test:
```python
@pytest.mark.asyncio
async def test_get_collection_non_owner_returns_403(auth_client, other_auth_client):
    resp = await auth_client.post("/collections", json={"name": "Rachel's Bags"})
    coll_id = resp.json()["id"]
    resp = await other_auth_client.get(f"/collections/{coll_id}")
    assert resp.status_code == 403
```

- [ ] **Step 2: Run to confirm failure**
```bash
python3 -m pytest tests/test_collections.py::test_get_collection_non_owner_returns_403 -v
```
Expected: FAIL — returns 200 instead of 403

- [ ] **Step 3: Fix collections route**

In `purseinator/routes/collections.py`, update `get_collection` to add ownership check:
```python
@router.get("/{collection_id}")
async def get_collection(
    collection_id: int,
    user: UserTable = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CollectionRead:
    result = await db.execute(
        select(CollectionTable).where(CollectionTable.id == collection_id)
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Collection not found")
    if row.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    return CollectionRead.model_validate(row)
```

- [ ] **Step 4: Run all collection tests**
```bash
python3 -m pytest tests/test_collections.py -v
```
Expected: all pass

- [ ] **Step 5: Commit**
```bash
git add tests/test_collections.py purseinator/routes/collections.py
git commit -m "feat: collection 403 for non-owner; add ownership check to get_collection"
```

---

### Task 4: Items — non-owner 403 on patch

**Background:** `GET /{item_id}` already returns 404 if the item doesn't belong to the given collection. `PATCH /{item_id}` (function name: `update_item`) already returns 404 for missing items, but has no ownership check — any authenticated user can patch any item if they know the IDs.

**Files:**
- Modify: `tests/test_items.py`
- Modify: `purseinator/routes/items.py`

- [ ] **Step 1: Write the failing test**

Add a second user fixture and the ownership test in `tests/test_items.py`:
```python
@pytest.fixture
async def other_auth_client(db_engine, db_session_factory, photo_storage_root):
    app = create_app(session_factory=db_session_factory, photo_storage_root=photo_storage_root)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/auth/magic-link", json={"email": "kimberly@example.com"})
        token = resp.json()["token"]
        resp = await ac.get(f"/auth/verify?token={token}")
        ac.cookies.set("session_id", resp.json()["session_id"])
        yield ac


@pytest.mark.asyncio
async def test_patch_item_non_owner_returns_403(auth_client, other_auth_client, collection_id, item_id):
    resp = await other_auth_client.patch(
        f"/collections/{collection_id}/items/{item_id}",
        json={"brand": "Gucci"},
    )
    assert resp.status_code == 403
```

Add the imports at the top of `tests/test_items.py` if not already present:
```python
from httpx import ASGITransport, AsyncClient
from purseinator.main import create_app
```

- [ ] **Step 2: Run to confirm failure**
```bash
python3 -m pytest tests/test_items.py::test_patch_item_non_owner_returns_403 -v
```
Expected: FAIL — returns 200 (no ownership check in `update_item`)

- [ ] **Step 3: Fix items route — add ownership check to update_item**

In `purseinator/routes/items.py`, replace the `update_item` function. Add `CollectionTable` to the import line first:
```python
from purseinator.models import CollectionTable, ItemRead, ItemTable, UserTable
```

Then replace `update_item`:
```python
@router.patch("/{item_id}")
async def update_item(
    collection_id: int,
    item_id: int,
    body: ItemUpdateBody,
    user: UserTable = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ItemRead:
    # Ownership check via collection
    coll_result = await db.execute(
        select(CollectionTable).where(CollectionTable.id == collection_id)
    )
    coll = coll_result.scalar_one_or_none()
    if coll is None or coll.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Forbidden")

    result = await db.execute(
        select(ItemTable).where(
            ItemTable.id == item_id, ItemTable.collection_id == collection_id
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Item not found")

    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(row, key, value)

    await db.commit()
    await db.refresh(row)
    return ItemRead.model_validate(row)
```

- [ ] **Step 4: Run all item tests**
```bash
python3 -m pytest tests/test_items.py -v
```
Expected: all pass

- [ ] **Step 5: Commit**
```bash
git add tests/test_items.py purseinator/routes/items.py
git commit -m "feat: item patch 403 for non-owner; add ownership check to update_item"
```

---

### Task 5: Photos — missing item 404 on upload

**Background:** `GET /photos/{key}` already returns 404 if the file doesn't exist (lines 75-76 in photos.py). The gap is `POST /photos`: it writes the file to disk even if `item_id` doesn't exist, creating orphan files.

**Files:**
- Modify: `tests/test_photos.py`
- Modify: `purseinator/routes/photos.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_photos.py`:
```python
@pytest.mark.asyncio
async def test_upload_photo_missing_item_returns_404(auth_client, collection_id):
    import io
    resp = await auth_client.post(
        f"/collections/{collection_id}/items/99999/photos",
        files={"file": ("bag.jpg", io.BytesIO(b"data"), "image/jpeg")},
    )
    assert resp.status_code == 404
```

- [ ] **Step 2: Run to confirm failure**
```bash
python3 -m pytest tests/test_photos.py::test_upload_photo_missing_item_returns_404 -v
```
Expected: FAIL — returns 201 (no item existence check)

- [ ] **Step 3: Fix photos route — check item exists before writing**

In `purseinator/routes/photos.py`, add `ItemTable` to the import line:
```python
from purseinator.models import ItemPhotoRead, ItemPhotoTable, ItemTable, UserTable
```

In `upload_photo`, add before `data = await file.read()`:
```python
    item = await db.get(ItemTable, item_id)
    if item is None or item.collection_id != collection_id:
        raise HTTPException(status_code=404, detail="Item not found")
```

- [ ] **Step 4: Run all photo tests**
```bash
python3 -m pytest tests/test_photos.py -v
```
Expected: all pass

- [ ] **Step 5: Commit**
```bash
git add tests/test_photos.py purseinator/routes/photos.py
git commit -m "feat: photo upload 404 when item does not exist"
```

---

### Task 6: Ranking — single item 404, invalid winner 422

**Files:**
- Modify: `tests/test_ranking.py`
- Modify: `purseinator/services/ranking.py`
- Modify: `purseinator/routes/ranking.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/test_ranking.py`:
```python
@pytest.mark.asyncio
async def test_next_pair_single_item_returns_404(auth_client):
    resp = await auth_client.post("/collections", json={"name": "Solo"})
    cid = resp.json()["id"]
    await auth_client.post(f"/collections/{cid}/items", json={"brand": "Coach"})
    resp = await auth_client.get(f"/collections/{cid}/ranking/next")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_submit_comparison_invalid_winner_returns_422(auth_client, collection_with_items):
    cid = collection_with_items
    pair = (await auth_client.get(f"/collections/{cid}/ranking/next")).json()
    resp = await auth_client.post(
        f"/collections/{cid}/ranking/compare",
        json={
            "item_a_id": pair["item_a"]["id"],
            "item_b_id": pair["item_b"]["id"],
            "winner_id": 99999,
            "info_level_shown": pair["info_level"],
        },
    )
    assert resp.status_code == 422
```

- [ ] **Step 2: Run to confirm failures**
```bash
python3 -m pytest tests/test_ranking.py::test_next_pair_single_item_returns_404 tests/test_ranking.py::test_submit_comparison_invalid_winner_returns_422 -v
```
Expected: both fail — single item crashes with IndexError → 500; invalid winner returns 201

- [ ] **Step 3: Fix services/ranking.py — handle single item in get_next_pair**

In `purseinator/services/ranking.py`, update `get_next_pair` to return `None` when fewer than 2 items:
```python
async def get_next_pair(
    db: AsyncSession, collection_id: int, user_id: int
) -> dict | None:
    await ensure_ratings(db, collection_id, user_id)

    result = await db.execute(
        select(EloRatingTable).where(
            EloRatingTable.collection_id == collection_id,
            EloRatingTable.user_id == user_id,
        )
    )
    ratings = result.scalars().all()
    if len(ratings) < 2:
        return None  # caller raises 404

    rating_tuples = [(r.item_id, r.rating, r.comparison_count) for r in ratings]
    item_a_id, item_b_id = select_pair(rating_tuples)

    rating_a = next(r for r in ratings if r.item_id == item_a_id)
    rating_b = next(r for r in ratings if r.item_id == item_b_id)
    gap = abs(rating_a.rating - rating_b.rating)
    info_level = info_level_for_gap(gap)

    item_a = await db.get(ItemTable, item_a_id)
    item_b = await db.get(ItemTable, item_b_id)

    return {
        "item_a": ItemRead.model_validate(item_a),
        "item_b": ItemRead.model_validate(item_b),
        "info_level": info_level,
    }
```

- [ ] **Step 4: Fix routes/ranking.py — raise 404 on None, validate winner via model_validator**

Replace `purseinator/routes/ranking.py` entirely:
```python
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, model_validator
from sqlalchemy.ext.asyncio import AsyncSession

from purseinator.deps import get_current_user, get_db
from purseinator.models import UserTable
from purseinator.services.ranking import get_next_pair, get_ranked_items, record_comparison

router = APIRouter()


class CompareRequest(BaseModel):
    item_a_id: int
    item_b_id: int
    winner_id: int
    info_level_shown: str

    @model_validator(mode="after")
    def winner_must_be_in_pair(self) -> "CompareRequest":
        if self.winner_id not in (self.item_a_id, self.item_b_id):
            raise ValueError("winner_id must be item_a_id or item_b_id")
        return self


@router.get("/next")
async def next_pair(
    collection_id: int,
    user: UserTable = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    pair = await get_next_pair(db, collection_id, user.id)
    await db.commit()
    if pair is None:
        raise HTTPException(status_code=404, detail="Not enough items to compare")
    return {
        "item_a": pair["item_a"].model_dump(),
        "item_b": pair["item_b"].model_dump(),
        "info_level": pair["info_level"],
    }


@router.post("/compare", status_code=201)
async def submit_comparison(
    collection_id: int,
    body: CompareRequest,
    user: UserTable = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await record_comparison(
        db,
        collection_id=collection_id,
        user_id=user.id,
        item_a_id=body.item_a_id,
        item_b_id=body.item_b_id,
        winner_id=body.winner_id,
        info_level_shown=body.info_level_shown,
    )
    await db.commit()
    return {"status": "recorded"}


@router.get("")
async def ranked_list(
    collection_id: int,
    user: UserTable = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    items = await get_ranked_items(db, collection_id, user.id)
    await db.commit()
    return items
```

- [ ] **Step 5: Run all ranking tests**
```bash
python3 -m pytest tests/test_ranking.py -v
```
Expected: all pass

- [ ] **Step 6: Commit**
```bash
git add tests/test_ranking.py purseinator/routes/ranking.py purseinator/services/ranking.py
git commit -m "feat: ranking single item 404, invalid winner 422"
```

---

### Task 7: Service unit tests — elo upset, pairing single item, ranking sort

**Files:**
- Modify: `tests/test_elo.py`
- Modify: `tests/test_pairing.py`
- Create: `tests/test_ranking_service.py`

- [ ] **Step 1: Write failing test for elo upset magnitude**

Add to `tests/test_elo.py`:
```python
def test_larger_upset_produces_larger_rating_change():
    # Big upset: low-rated beats high-rated
    big_winner_new, _ = calculate_new_ratings(1200, 1800, k_factor=32)
    # Small upset: near-equal ratings
    small_winner_new, _ = calculate_new_ratings(1490, 1510, k_factor=32)
    big_change = big_winner_new - 1200
    small_change = small_winner_new - 1490
    assert big_change > small_change
```

- [ ] **Step 2: Run elo test to see if it passes already**
```bash
python3 -m pytest tests/test_elo.py::test_larger_upset_produces_larger_rating_change -v
```
Expected: PASS (elo math already handles this). If it fails, review `calculate_new_ratings` in `purseinator/services/elo.py`.

- [ ] **Step 3: Write failing test for pairing single item**

Add to `tests/test_pairing.py`:
```python
def test_select_pair_single_item_raises():
    with pytest.raises((IndexError, ValueError)):
        select_pair([(1, 1500, 0)])
```

- [ ] **Step 4: Run pairing test**
```bash
python3 -m pytest tests/test_pairing.py::test_select_pair_single_item_raises -v
```
Expected: PASS (currently raises IndexError on `pool[1][0]`).

- [ ] **Step 5: Write failing ranking service unit tests**

Create `tests/test_ranking_service.py`:
```python
from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from purseinator.models import Base, CollectionTable, EloRatingTable, ItemTable, UserTable
from purseinator.services.ranking import ensure_ratings, get_ranked_items


@pytest.fixture
async def db_with_user_and_collection():
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as db:
        user = UserTable(email="test@example.com", name="Test", role="curator")
        db.add(user)
        await db.flush()
        coll = CollectionTable(owner_id=user.id, name="Test Collection")
        db.add(coll)
        await db.flush()
        yield db, user.id, coll.id
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.mark.asyncio
async def test_ranked_items_sorted_by_rating_descending(db_with_user_and_collection):
    db, user_id, coll_id = db_with_user_and_collection
    for brand, rating in [("A", 1600.0), ("B", 1400.0), ("C", 1550.0)]:
        item = ItemTable(collection_id=coll_id, brand=brand)
        db.add(item)
        await db.flush()
        db.add(EloRatingTable(
            item_id=item.id, collection_id=coll_id, user_id=user_id,
            rating=rating, comparison_count=0
        ))
    await db.commit()

    ranked = await get_ranked_items(db, coll_id, user_id)
    ratings = [r["rating"] for r in ranked]
    assert ratings == sorted(ratings, reverse=True)
    assert ratings[0] == 1600.0


@pytest.mark.asyncio
async def test_ensure_ratings_creates_missing_elo_rows(db_with_user_and_collection):
    db, user_id, coll_id = db_with_user_and_collection
    item = ItemTable(collection_id=coll_id, brand="Coach")
    db.add(item)
    await db.commit()

    await ensure_ratings(db, coll_id, user_id)
    await db.commit()

    result = await db.execute(
        select(EloRatingTable).where(
            EloRatingTable.collection_id == coll_id,
            EloRatingTable.user_id == user_id,
        )
    )
    rows = result.scalars().all()
    assert len(rows) == 1
    assert rows[0].rating == 1500.0
```

- [ ] **Step 6: Run ranking service tests to confirm failures**
```bash
python3 -m pytest tests/test_ranking_service.py -v
```
Expected: tests fail if `get_ranked_items` or `ensure_ratings` don't behave as expected. If they pass immediately, that's fine — these are behavior-verifying tests.

- [ ] **Step 7: Run full suite**
```bash
python3 -m pytest tests/ -q
```
Expected: all non-GPU tests pass

- [ ] **Step 8: Commit**
```bash
git add tests/test_elo.py tests/test_pairing.py tests/test_ranking_service.py
git commit -m "test: service unit gaps — elo upset magnitude, pairing single item, ranking sort"
```

---

### Task 8: Full suite green + push

- [ ] **Step 1: Run full suite**
```bash
python3 -m pytest tests/ -q
```
Expected: all non-GPU tests pass, GPU tests skipped

- [ ] **Step 2: Push**
```bash
git push origin main
```
