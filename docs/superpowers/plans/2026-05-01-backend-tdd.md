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
cd /path/to/purseinator
python3 -m pytest tests/ -q
```
Expected: 70 passed, 4+ skipped, 0 errors

- [ ] **Step 5: Commit**
```bash
git add tests/test_card_detector.py tests/test_condition.py tests/test_grouper.py tests/test_integration.py
git commit -m "test: skip gpu-dependent tests when numpy is absent"
```

---

### Task 2: Auth gaps — missing email 422, token reuse 401, /me fields

**Files:**
- Modify: `tests/test_auth.py`
- Modify: `purseinator/routes/auth.py` (if needed)

- [ ] **Step 1: Write failing tests**

Add to `tests/test_auth.py`:
```python
@pytest.mark.asyncio
async def test_magic_link_missing_email_returns_422(db_client):
    resp = await db_client.post("/auth/magic-link", json={})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_verify_token_reuse_returns_401(db_client):
    resp = await db_client.post("/auth/magic-link", json={"email": "rachel@example.com"})
    token = resp.json()["token"]
    # First use — should succeed
    await db_client.get(f"/auth/verify?token={token}")
    # Second use — should fail
    resp = await db_client.get(f"/auth/verify?token={token}")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me_returns_name_and_role(db_client):
    resp = await db_client.post("/auth/magic-link", json={"email": "rachel@example.com"})
    token = resp.json()["token"]
    resp = await db_client.get(f"/auth/verify?token={token}")
    session_id = resp.json()["session_id"]
    resp = await db_client.get("/auth/me", cookies={"session_id": session_id})
    assert resp.status_code == 200
    data = resp.json()
    assert "name" in data
    assert "role" in data
```

- [ ] **Step 2: Run to confirm failures**
```bash
python3 -m pytest tests/test_auth.py::test_magic_link_missing_email_returns_422 tests/test_auth.py::test_verify_token_reuse_returns_401 tests/test_auth.py::test_me_returns_name_and_role -v
```
Expected: the 422 test may pass (FastAPI Pydantic validation), token reuse and name/role may fail.

- [ ] **Step 3: Read current auth route**

Open `purseinator/routes/auth.py`. Find the `/verify` endpoint. Check whether it invalidates the token after use. If not, add invalidation:
```python
# After creating the session, delete or mark the token used:
await db.delete(token_row)  # or token_row.used = True
await db.commit()
```
Check `/me` endpoint returns `name` and `role` in its response schema.

- [ ] **Step 4: Run tests to confirm all pass**
```bash
python3 -m pytest tests/test_auth.py -v
```
Expected: all pass

- [ ] **Step 5: Commit**
```bash
git add tests/test_auth.py purseinator/routes/auth.py
git commit -m "test: auth gaps — 422 on missing email, 401 on token reuse, name+role in /me"
```

---

### Task 3: Collections — non-owner gets 403

**Files:**
- Modify: `tests/test_collections.py`
- Modify: `purseinator/routes/collections.py`

- [ ] **Step 1: Write failing test**

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

Add the test:
```python
from httpx import ASGITransport, AsyncClient
from purseinator.main import create_app

@pytest.mark.asyncio
async def test_get_collection_non_owner_returns_403(auth_client, other_auth_client):
    resp = await auth_client.post("/collections", json={"name": "Rachel's Bags"})
    coll_id = resp.json()["id"]
    resp = await other_auth_client.get(f"/collections/{coll_id}")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_list_collections_scoped_to_user(auth_client, other_auth_client):
    await auth_client.post("/collections", json={"name": "Rachel's Bags"})
    resp = await other_auth_client.get("/collections")
    assert resp.status_code == 200
    assert len(resp.json()) == 0
```

- [ ] **Step 2: Run to confirm failures**
```bash
python3 -m pytest tests/test_collections.py::test_get_collection_non_owner_returns_403 tests/test_collections.py::test_list_collections_scoped_to_user -v
```
Expected: `test_get_collection_non_owner_returns_403` FAILS (currently returns 200)

- [ ] **Step 3: Fix collections route**

In `purseinator/routes/collections.py`, update `get_collection`:
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
git commit -m "test: collection 403 for non-owner; fix get_collection ownership check"
```

---

### Task 4: Items — wrong collection 404, non-owner 403, missing item 404

**Files:**
- Modify: `tests/test_items.py`
- Modify: `purseinator/routes/items.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/test_items.py`:
```python
from httpx import ASGITransport, AsyncClient
from purseinator.main import create_app

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
async def test_get_item_wrong_collection_returns_404(auth_client, collection_id, item_id):
    other_resp = await auth_client.post("/collections", json={"name": "Other"})
    other_cid = other_resp.json()["id"]
    resp = await auth_client.get(f"/collections/{other_cid}/items/{item_id}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_patch_item_missing_returns_404(auth_client, collection_id):
    resp = await auth_client.patch(
        f"/collections/{collection_id}/items/99999",
        json={"brand": "Gucci"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_patch_item_non_owner_returns_403(auth_client, other_auth_client, collection_id, item_id):
    resp = await other_auth_client.patch(
        f"/collections/{collection_id}/items/{item_id}",
        json={"brand": "Gucci"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_create_item_default_status_is_undecided(auth_client, collection_id):
    resp = await auth_client.post(f"/collections/{collection_id}/items", json={})
    assert resp.status_code == 201
    assert resp.json()["status"] == "undecided"
```

- [ ] **Step 2: Run to confirm failures**
```bash
python3 -m pytest tests/test_items.py::test_get_item_wrong_collection_returns_404 tests/test_items.py::test_patch_item_missing_returns_404 tests/test_items.py::test_patch_item_non_owner_returns_403 -v
```
Expected: all fail

- [ ] **Step 3: Read full items route**

Read `purseinator/routes/items.py` in full to see get_item and patch_item implementations.

- [ ] **Step 4: Fix items route — add ownership and collection-scoping checks**

Update `get_item` to verify item belongs to the given collection:
```python
@router.get("/{item_id}")
async def get_item(
    collection_id: int,
    item_id: int,
    user: UserTable = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ItemRead:
    row = await db.get(ItemTable, item_id)
    if row is None or row.collection_id != collection_id:
        raise HTTPException(status_code=404, detail="Item not found")
    return ItemRead.model_validate(row)
```

Update `patch_item` to verify ownership via collection:
```python
@router.patch("/{item_id}")
async def patch_item(
    collection_id: int,
    item_id: int,
    body: ItemUpdateBody,
    user: UserTable = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ItemRead:
    # Check collection ownership
    coll_result = await db.execute(
        select(CollectionTable).where(CollectionTable.id == collection_id)
    )
    coll = coll_result.scalar_one_or_none()
    if coll is None or coll.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    row = await db.get(ItemTable, item_id)
    if row is None or row.collection_id != collection_id:
        raise HTTPException(status_code=404, detail="Item not found")
    if body.brand is not None:
        row.brand = body.brand
    if body.description is not None:
        row.description = body.description
    if body.condition_score is not None:
        row.condition_score = body.condition_score
    if body.status is not None:
        row.status = body.status
    await db.commit()
    await db.refresh(row)
    return ItemRead.model_validate(row)
```

Add `from purseinator.models import CollectionTable` import if not present.

- [ ] **Step 5: Run all item tests**
```bash
python3 -m pytest tests/test_items.py -v
```
Expected: all pass

- [ ] **Step 6: Commit**
```bash
git add tests/test_items.py purseinator/routes/items.py
git commit -m "test: items gaps — wrong collection 404, missing 404, non-owner 403"
```

---

### Task 5: Photos — missing item 404, missing storage key 404

**Files:**
- Modify: `tests/test_photos.py`
- Modify: `purseinator/routes/photos.py`

- [ ] **Step 1: Write failing tests**

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


@pytest.mark.asyncio
async def test_serve_missing_photo_returns_404(auth_client):
    resp = await auth_client.get("/photos/nonexistent-key.jpg")
    assert resp.status_code == 404
```

- [ ] **Step 2: Run to confirm failures**
```bash
python3 -m pytest tests/test_photos.py::test_upload_photo_missing_item_returns_404 tests/test_photos.py::test_serve_missing_photo_returns_404 -v
```
Expected: both fail

- [ ] **Step 3: Read photos route**

Open `purseinator/routes/photos.py` and find the upload and serve endpoints.

- [ ] **Step 4: Fix photos route — add 404 checks**

In the upload handler, verify item exists before writing:
```python
item = await db.get(ItemTable, item_id)
if item is None or item.collection_id != collection_id:
    raise HTTPException(status_code=404, detail="Item not found")
```

In the serve handler, check file exists before streaming:
```python
import os
full_path = os.path.join(photo_storage_root, storage_key)
if not os.path.exists(full_path):
    raise HTTPException(status_code=404, detail="Photo not found")
```

- [ ] **Step 5: Run all photo tests**
```bash
python3 -m pytest tests/test_photos.py -v
```
Expected: all pass

- [ ] **Step 6: Commit**
```bash
git add tests/test_photos.py purseinator/routes/photos.py
git commit -m "test: photos gaps — missing item 404 on upload, missing key 404 on serve"
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
Expected: both fail (single item crashes with IndexError; invalid winner returns 201)

- [ ] **Step 3: Fix services/ranking.py — handle single item in get_next_pair**

In `purseinator/services/ranking.py`, update `get_next_pair`:
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

- [ ] **Step 4: Fix routes/ranking.py — raise 404 on None, validate winner**

```python
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
git commit -m "test: ranking gaps — single item 404, invalid winner 422"
```

---

### Task 7: Service unit tests — elo upset, pairing single item, ranking sort

**Files:**
- Modify: `tests/test_elo.py`
- Modify: `tests/test_pairing.py`
- Create: `tests/test_ranking_service.py`

- [ ] **Step 1: Write failing tests for elo**

Add to `tests/test_elo.py`:
```python
def test_larger_upset_produces_larger_rating_change():
    # Big upset: low-rated beats high-rated
    big_winner_new, big_loser_new = calculate_new_ratings(1200, 1800, k_factor=32)
    # Small upset: near-equal ratings
    small_winner_new, small_loser_new = calculate_new_ratings(1490, 1510, k_factor=32)
    big_change = big_winner_new - 1200
    small_change = small_winner_new - 1490
    assert big_change > small_change
```

- [ ] **Step 2: Write failing test for pairing single item**

Add to `tests/test_pairing.py`:
```python
def test_select_pair_single_item_raises():
    with pytest.raises((IndexError, ValueError)):
        select_pair([(1, 1500, 0)])
```

- [ ] **Step 3: Write ranking service unit tests**

Create `tests/test_ranking_service.py`:
```python
from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from purseinator.models import Base, CollectionTable, EloRatingTable, ItemTable, UserTable
from purseinator.services.ranking import get_ranked_items, ensure_ratings


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

    from sqlalchemy import select
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

- [ ] **Step 4: Run to confirm failures**
```bash
python3 -m pytest tests/test_elo.py::test_larger_upset_produces_larger_rating_change tests/test_pairing.py::test_select_pair_single_item_raises tests/test_ranking_service.py -v
```

- [ ] **Step 5: Check if elo test passes already**

The elo math already handles upsets correctly — `test_larger_upset_produces_larger_rating_change` should pass. If it fails, review `expected_score` and `calculate_new_ratings` in `purseinator/services/elo.py`.

- [ ] **Step 6: Run full suite**
```bash
python3 -m pytest tests/ -q
```
Expected: all non-GPU tests pass

- [ ] **Step 7: Commit**
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
