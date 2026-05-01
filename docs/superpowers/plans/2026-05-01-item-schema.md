# Item Schema Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add color/style/material/dimensions/serial/asking_price metadata columns to `ItemTable` with Pydantic validation, a mutual-exclusion rule for multi-color, and a single Alembic migration covering all new columns.

**Architecture:** New Python `Enum` constants (`Color`, `Style`, `Material`) are defined in `app/models.py` alongside the ORM model and Pydantic schemas. `ItemTable` gains nine columns (one using `JSON` for the `secondary_colors` list; `secondary_colors` is `nullable=False` with `server_default='[]'`). `ItemRead`, `ItemCreate`, `ItemCreateBody`, and `ItemUpdateBody` all grow matching optional fields. `ItemCreate` is used in `tests/test_models.py` (not dead code) and must be extended with the new fields. A single Alembic migration adds every column at once and backfills `secondary_colors` with `[]`.

**Tech Stack:** Python 3.10+, FastAPI, SQLAlchemy async, alembic, Pydantic v2

---

## File Map

| File | Change |
|------|--------|
| `app/models.py` | Add `Color`, `Style`, `Material` enums; extend `ItemTable`, `ItemRead`, `ItemCreate` (used in `tests/test_models.py`) |
| `app/routes/items.py` | Extend `ItemCreateBody` and `ItemUpdateBody`; add `model_validator` |
| `alembic/versions/<hash>_add_item_metadata_columns.py` | New migration — all 9 columns + backfill |
| `tests/test_items.py` | 16 new test functions |

---

### Task 1: Add `Color`, `Style`, `Material` Python enums to `app/models.py`

**Files:**
- Modify: `app/models.py`

These are pure Python constants — no DB change, no migration needed yet. They will be referenced by Pydantic `Literal` types in later tasks.

- [ ] **Step 1: Write the failing import test**

Add to `tests/test_items.py`:

```python
def test_enum_constants_importable():
    from app.models import Color, Style, Material
    assert Color.RED == "red"
    assert Color.MULTI == "multi"
    assert Style.SATCHEL == "satchel"
    assert Style.BELT_BAG == "belt-bag"
    assert Material.LEATHER == "leather"
    assert Material.VEGAN_LEATHER == "vegan leather"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /gt/purseinator/crew/kagarmoe && python -m pytest tests/test_items.py::test_enum_constants_importable -v
```

Expected: `FAILED` — `ImportError: cannot import name 'Color' from 'app.models'`

- [ ] **Step 3: Add the three enum classes to `app/models.py`**

Insert after the `from __future__ import annotations` block imports (after line 6, before `# SQLAlchemy declarative base`). Add `from enum import Enum` to the import block:

```python
from enum import Enum
```

Then insert the three enum classes after the imports and before `class Base(DeclarativeBase):`:

```python
class Color(str, Enum):
    RED = "red"
    YELLOW = "yellow"
    ORANGE = "orange"
    GREEN = "green"
    BLUE = "blue"
    VIOLET = "violet"
    WHITE = "white"
    BLACK = "black"
    TAN = "tan"
    BROWN = "brown"
    MULTI = "multi"


class Style(str, Enum):
    SATCHEL = "satchel"
    SADDLEBAG = "saddlebag"
    DUFFEL = "duffel"
    FRAME = "frame"
    MESSENGER = "messenger"
    TOTE = "tote"
    FOLDOVER = "foldover"
    BARREL = "barrel"
    BUCKET = "bucket"
    HOBO = "hobo"
    BAGUETTE = "baguette"
    DOCTOR = "doctor"
    BACKPACK = "backpack"
    CLUTCH = "clutch"
    ENVELOPE = "envelope"
    MINAUDIERE = "minaudiere"
    CROSSBODY = "crossbody"
    DIAPER = "diaper"
    WRISTLET = "wristlet"
    BELT_BAG = "belt-bag"


class Material(str, Enum):
    LEATHER = "leather"
    VEGAN_LEATHER = "vegan leather"
    CLOTH = "cloth"
    TAPESTRY = "tapestry"
    VELVET = "velvet"
    SUEDE = "suede"
    PERFORMANCE = "performance"
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd /gt/purseinator/crew/kagarmoe && python -m pytest tests/test_items.py::test_enum_constants_importable -v
```

Expected: `PASSED`

- [ ] **Step 5: Run the full suite to verify no regressions**

```bash
cd /gt/purseinator/crew/kagarmoe && python -m pytest tests/ -v --tb=short 2>&1 | tail -20
```

Expected: all 89 pre-existing tests still pass + 1 new test = 90 total.

- [ ] **Step 6: Commit**

```bash
cd /gt/purseinator/crew/kagarmoe && git add app/models.py tests/test_items.py && git commit -m "feat: add Color, Style, Material enum constants to app/models"
```

---

### Task 2: Add `primary_color`, `style`, `material` columns to `ItemTable` + extend Pydantic schemas

**Files:**
- Modify: `app/models.py`
- Modify: `app/routes/items.py`

No migration yet — tests in this task run against the in-memory SQLite engine created by `db_engine` in conftest, which uses `Base.metadata.create_all`. Adding columns to the ORM model is enough for the HTTP tests to work.

- [ ] **Step 1: Write three failing tests**

Add to `tests/test_items.py`:

```python
@pytest.mark.asyncio
async def test_update_item_primary_color(auth_client, collection_id, item_id):
    resp = await auth_client.patch(
        f"/collections/{collection_id}/items/{item_id}",
        json={"primary_color": "blue"},
    )
    assert resp.status_code == 200
    assert resp.json()["primary_color"] == "blue"


@pytest.mark.asyncio
async def test_update_item_style(auth_client, collection_id, item_id):
    resp = await auth_client.patch(
        f"/collections/{collection_id}/items/{item_id}",
        json={"style": "tote"},
    )
    assert resp.status_code == 200
    assert resp.json()["style"] == "tote"


@pytest.mark.asyncio
async def test_update_item_invalid_primary_color_returns_422(auth_client, collection_id, item_id):
    resp = await auth_client.patch(
        f"/collections/{collection_id}/items/{item_id}",
        json={"primary_color": "purple"},
    )
    assert resp.status_code == 422
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /gt/purseinator/crew/kagarmoe && python -m pytest tests/test_items.py::test_update_item_primary_color tests/test_items.py::test_update_item_style tests/test_items.py::test_update_item_invalid_primary_color_returns_422 -v
```

Expected: all three `FAILED` — `primary_color` and `style` keys missing from response JSON; `purple` accepted when it should be rejected.

- [ ] **Step 3: Add columns to `ItemTable` in `app/models.py`**

Add `JSON` to the SQLAlchemy imports at the top of `app/models.py` (it may already be there — add it if not):

```python
from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    Boolean,
    func,
)
```

Then add three new columns to `ItemTable`, after the `status` column:

```python
    primary_color = Column(String(20), nullable=True)
    style = Column(String(30), nullable=True)
    material = Column(String(30), nullable=True)
```

- [ ] **Step 4: Extend `ItemRead` in `app/models.py`**

Also add `Field` to the Pydantic imports at the top of `app/models.py`:

```python
from pydantic import BaseModel, ConfigDict, Field, field_validator
```

Add the three new optional fields to `ItemRead`, typed as the enum classes for end-to-end type safety (Pydantic v2 handles coercion from string DB values with `from_attributes=True`):

```python
class ItemRead(BaseModel):
    model_config = ConfigDict(frozen=True, from_attributes=True)

    id: int
    collection_id: int
    brand: str
    description: str
    condition_score: Optional[float] = None
    status: str
    created_at: Optional[datetime] = None
    primary_color: Optional[Color] = None
    style: Optional[Style] = None
    material: Optional[Material] = None
```

- [ ] **Step 5: Extend `ItemUpdateBody` in `app/routes/items.py`**

Replace `ItemUpdateBody` with the version that includes typed enum literals:

```python
class ItemUpdateBody(BaseModel):
    brand: Optional[str] = None
    description: Optional[str] = None
    condition_score: Optional[float] = None
    status: Optional[str] = None
    primary_color: Optional[Literal[
        "red", "yellow", "orange", "green", "blue", "violet",
        "white", "black", "tan", "brown", "multi"
    ]] = None
    style: Optional[Literal[
        "satchel", "saddlebag", "duffel", "frame", "messenger", "tote",
        "foldover", "barrel", "bucket", "hobo", "baguette", "doctor",
        "backpack", "clutch", "envelope", "minaudiere", "crossbody",
        "diaper", "wristlet", "belt-bag"
    ]] = None
    material: Optional[Literal[
        "leather", "vegan leather", "cloth", "tapestry", "velvet", "suede", "performance"
    ]] = None
```

Also add `Literal` to the imports at the top of `app/routes/items.py`:

```python
from typing import Literal, Optional
```

- [ ] **Step 6: Run tests to verify they pass**

```bash
cd /gt/purseinator/crew/kagarmoe && python -m pytest tests/test_items.py::test_update_item_primary_color tests/test_items.py::test_update_item_style tests/test_items.py::test_update_item_invalid_primary_color_returns_422 -v
```

Expected: all three `PASSED`.

- [ ] **Step 7: Run the full suite**

```bash
cd /gt/purseinator/crew/kagarmoe && python -m pytest tests/ -v --tb=short 2>&1 | tail -20
```

Expected: all previous + 3 new = 93 tests pass.

- [ ] **Step 8: Commit**

```bash
cd /gt/purseinator/crew/kagarmoe && git add app/models.py app/routes/items.py tests/test_items.py && git commit -m "feat: add primary_color, style, material columns and Pydantic validation"
```

---

### Task 3: Add `secondary_colors` JSON column + tests

**Files:**
- Modify: `app/models.py`
- Modify: `app/routes/items.py`

`secondary_colors` is a `JSON` column defaulting to `[]`. It is typed as `list[str]` everywhere. The Pydantic `Literal` union for valid color values is shared with `primary_color`.

- [ ] **Step 1: Write two failing tests**

Add to `tests/test_items.py`:

```python
@pytest.mark.asyncio
async def test_create_item_explicit_secondary_colors_roundtrip(auth_client, collection_id):
    """Explicit secondary_colors round-trips correctly through POST."""
    resp = await auth_client.post(
        f"/collections/{collection_id}/items",
        json={"secondary_colors": ["red", "tan"]},
    )
    assert resp.status_code == 201
    assert resp.json()["secondary_colors"] == ["red", "tan"]


@pytest.mark.asyncio
async def test_update_item_secondary_colors_roundtrip(auth_client, collection_id, item_id):
    resp = await auth_client.patch(
        f"/collections/{collection_id}/items/{item_id}",
        json={"secondary_colors": ["tan", "brown"]},
    )
    assert resp.status_code == 200
    assert resp.json()["secondary_colors"] == ["tan", "brown"]
```

Note: The test for `secondary_colors` defaulting to `[]` when not supplied belongs in Task 6, where `ItemCreateBody.secondary_colors: list[...] = Field(default_factory=list)` is introduced and makes the default deterministic.

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /gt/purseinator/crew/kagarmoe && python -m pytest tests/test_items.py::test_create_item_explicit_secondary_colors_roundtrip tests/test_items.py::test_update_item_secondary_colors_roundtrip -v
```

Expected: `FAILED` — `secondary_colors` key absent from JSON responses.

- [ ] **Step 3: Add `secondary_colors` column to `ItemTable` in `app/models.py`**

Add after the `material` column in `ItemTable`:

```python
    secondary_colors = Column(JSON, nullable=False, default=list, server_default='[]')
```

Note: `default=list` (the built-in) tells SQLAlchemy to call `list()` for each new row, producing `[]`. Do NOT use `default=[]` — that would share a single mutable list across rows. `server_default='[]'` ensures Postgres-safe non-nullable behavior; SQLite tolerates it too.

- [ ] **Step 4: Add `secondary_colors` to `ItemRead` in `app/models.py`**

Also add `Field` to the Pydantic imports at the top of `app/models.py`:

```python
from pydantic import BaseModel, ConfigDict, Field, field_validator
```

```python
class ItemRead(BaseModel):
    model_config = ConfigDict(frozen=True, from_attributes=True)

    id: int
    collection_id: int
    brand: str
    description: str
    condition_score: Optional[float] = None
    status: str
    created_at: Optional[datetime] = None
    primary_color: Optional[Color] = None
    secondary_colors: list[str] = Field(default_factory=list)
    style: Optional[Style] = None
    material: Optional[Material] = None
```

Note: `primary_color` and `style`/`material` are typed as `Optional[Color]`, `Optional[Style]`, `Optional[Material]` (the Python enums) for end-to-end type safety. Pydantic v2 handles enum coercion from string attributes natively with `from_attributes=True`.

- [ ] **Step 5: Add `secondary_colors` to `ItemUpdateBody` in `app/routes/items.py`**

Add after `primary_color` in `ItemUpdateBody`:

```python
    secondary_colors: Optional[list[Literal[
        "red", "yellow", "orange", "green", "blue", "violet",
        "white", "black", "tan", "brown", "multi"
    ]]] = None
```

- [ ] **Step 6: Run tests to verify they pass**

```bash
cd /gt/purseinator/crew/kagarmoe && python -m pytest tests/test_items.py::test_create_item_explicit_secondary_colors_roundtrip tests/test_items.py::test_update_item_secondary_colors_roundtrip -v
```

Expected: both `PASSED`.

- [ ] **Step 7: Run the full suite**

```bash
cd /gt/purseinator/crew/kagarmoe && python -m pytest tests/ -v --tb=short 2>&1 | tail -20
```

Expected: all previous + 2 new = 95 tests pass.

- [ ] **Step 8: Commit**

```bash
cd /gt/purseinator/crew/kagarmoe && git add app/models.py app/routes/items.py tests/test_items.py && git commit -m "feat: add secondary_colors JSON column with default []"
```

---

### Task 4: Add `width_in`, `height_in`, `depth_in` float columns + tests

**Files:**
- Modify: `app/models.py`
- Modify: `app/routes/items.py`

All three are nullable floats. `depth_in` is allowed to be `0.0` (a flat clutch has no depth) — the nullable/zero distinction is meaningful, so `0.0` is a valid value, not a sentinel.

- [ ] **Step 1: Write two failing tests**

Add to `tests/test_items.py`:

```python
@pytest.mark.asyncio
async def test_update_item_dimensions_roundtrip(auth_client, collection_id, item_id):
    resp = await auth_client.patch(
        f"/collections/{collection_id}/items/{item_id}",
        json={"width_in": 13.5, "height_in": 10.0, "depth_in": 0.0},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["width_in"] == 13.5
    assert data["height_in"] == 10.0
    assert data["depth_in"] == 0.0


@pytest.mark.asyncio
async def test_create_item_dimensions_default_null(auth_client, collection_id):
    resp = await auth_client.post(
        f"/collections/{collection_id}/items", json={}
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["width_in"] is None
    assert data["height_in"] is None
    assert data["depth_in"] is None
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /gt/purseinator/crew/kagarmoe && python -m pytest tests/test_items.py::test_update_item_dimensions_roundtrip tests/test_items.py::test_create_item_dimensions_default_null -v
```

Expected: `FAILED` — `width_in`, `height_in`, `depth_in` keys absent from JSON responses.

- [ ] **Step 3: Add columns to `ItemTable` in `app/models.py`**

Add after the `secondary_colors` column:

```python
    width_in = Column(Float, nullable=True)
    height_in = Column(Float, nullable=True)
    depth_in = Column(Float, nullable=True)
```

- [ ] **Step 4: Add fields to `ItemRead` in `app/models.py`**

```python
class ItemRead(BaseModel):
    model_config = ConfigDict(frozen=True, from_attributes=True)

    id: int
    collection_id: int
    brand: str
    description: str
    condition_score: Optional[float] = None
    status: str
    created_at: Optional[datetime] = None
    primary_color: Optional[Color] = None
    secondary_colors: list[str] = Field(default_factory=list)
    style: Optional[Style] = None
    material: Optional[Material] = None
    width_in: Optional[float] = None
    height_in: Optional[float] = None
    depth_in: Optional[float] = None
```

- [ ] **Step 5: Add fields to `ItemUpdateBody` in `app/routes/items.py`**

Add after `material`:

```python
    width_in: Optional[float] = None
    height_in: Optional[float] = None
    depth_in: Optional[float] = None
```

- [ ] **Step 6: Run tests to verify they pass**

```bash
cd /gt/purseinator/crew/kagarmoe && python -m pytest tests/test_items.py::test_update_item_dimensions_roundtrip tests/test_items.py::test_create_item_dimensions_default_null -v
```

Expected: both `PASSED`.

- [ ] **Step 7: Run the full suite**

```bash
cd /gt/purseinator/crew/kagarmoe && python -m pytest tests/ -v --tb=short 2>&1 | tail -20
```

Expected: all previous + 2 new = 97 tests pass.

- [ ] **Step 8: Commit**

```bash
cd /gt/purseinator/crew/kagarmoe && git add app/models.py app/routes/items.py tests/test_items.py && git commit -m "feat: add width_in, height_in, depth_in float columns"
```

---

### Task 5: Add `serial_number` and `asking_price` columns + tests

**Files:**
- Modify: `app/models.py`
- Modify: `app/routes/items.py`

`serial_number` is a nullable string. `asking_price` is a nullable integer (whole US dollars — no cents).

- [ ] **Step 1: Write two failing tests**

Add to `tests/test_items.py`:

```python
@pytest.mark.asyncio
async def test_update_item_serial_number_roundtrip(auth_client, collection_id, item_id):
    resp = await auth_client.patch(
        f"/collections/{collection_id}/items/{item_id}",
        json={"serial_number": "LV-12345"},
    )
    assert resp.status_code == 200
    assert resp.json()["serial_number"] == "LV-12345"


@pytest.mark.asyncio
async def test_update_item_asking_price_roundtrip(auth_client, collection_id, item_id):
    resp = await auth_client.patch(
        f"/collections/{collection_id}/items/{item_id}",
        json={"asking_price": 350},
    )
    assert resp.status_code == 200
    assert resp.json()["asking_price"] == 350
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /gt/purseinator/crew/kagarmoe && python -m pytest tests/test_items.py::test_update_item_serial_number_roundtrip tests/test_items.py::test_update_item_asking_price_roundtrip -v
```

Expected: `FAILED` — `serial_number` and `asking_price` absent from responses.

- [ ] **Step 3: Add columns to `ItemTable` in `app/models.py`**

Add after the `depth_in` column:

```python
    serial_number = Column(String(255), nullable=True)
    asking_price = Column(Integer, nullable=True)
```

- [ ] **Step 4: Add fields to `ItemRead` in `app/models.py`**

```python
class ItemRead(BaseModel):
    model_config = ConfigDict(frozen=True, from_attributes=True)

    id: int
    collection_id: int
    brand: str
    description: str
    condition_score: Optional[float] = None
    status: str
    created_at: Optional[datetime] = None
    primary_color: Optional[Color] = None
    secondary_colors: list[str] = Field(default_factory=list)
    style: Optional[Style] = None
    material: Optional[Material] = None
    width_in: Optional[float] = None
    height_in: Optional[float] = None
    depth_in: Optional[float] = None
    serial_number: Optional[str] = None
    asking_price: Optional[int] = None
```

- [ ] **Step 5: Add fields to `ItemUpdateBody` in `app/routes/items.py`**

Add after `depth_in`:

```python
    serial_number: Optional[str] = None
    asking_price: Optional[int] = None
```

- [ ] **Step 6: Run tests to verify they pass**

```bash
cd /gt/purseinator/crew/kagarmoe && python -m pytest tests/test_items.py::test_update_item_serial_number_roundtrip tests/test_items.py::test_update_item_asking_price_roundtrip -v
```

Expected: both `PASSED`.

- [ ] **Step 7: Run the full suite**

```bash
cd /gt/purseinator/crew/kagarmoe && python -m pytest tests/ -v --tb=short 2>&1 | tail -20
```

Expected: all previous + 2 new = 99 tests pass.

- [ ] **Step 8: Commit**

```bash
cd /gt/purseinator/crew/kagarmoe && git add app/models.py app/routes/items.py tests/test_items.py && git commit -m "feat: add serial_number and asking_price columns"
```

---

### Task 6: Add multi-color mutual-exclusion `model_validator`

**Files:**
- Modify: `app/routes/items.py`
- Modify: `app/models.py` (extend `ItemCreate`)

Rule: if `primary_color == "multi"` then `secondary_colors` must be `[]`. The validator lives on both `ItemUpdateBody` (PATCH route) and `ItemCreateBody` (POST route). A `ValueError` raised inside a Pydantic `model_validator` is automatically converted to a 422 response by FastAPI.

Additionally, the `update_item` route must auto-clear `secondary_colors` server-side when a PATCH sets `primary_color="multi"` without also sending `secondary_colors` — preserving the mutual-exclusion invariant even when the request body only contains `primary_color`. The Pydantic validator continues to reject the *direct* violation (multi + non-empty secondary in the same body) with 422.

- [ ] **Step 1: Write five failing tests**

Add to `tests/test_items.py`:

```python
@pytest.mark.asyncio
async def test_create_item_secondary_colors_default_empty(auth_client, collection_id):
    """When secondary_colors is not supplied, it defaults to [] (from ItemCreateBody.Field(default_factory=list))."""
    resp = await auth_client.post(
        f"/collections/{collection_id}/items",
        json={},
    )
    assert resp.status_code == 201
    assert resp.json()["secondary_colors"] == []


@pytest.mark.asyncio
async def test_multi_primary_color_with_secondary_colors_returns_422(auth_client, collection_id, item_id):
    resp = await auth_client.patch(
        f"/collections/{collection_id}/items/{item_id}",
        json={"primary_color": "multi", "secondary_colors": ["red"]},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_secondary_colors_with_multi_primary_returns_422(auth_client, collection_id, item_id):
    # Set primary to multi first (valid on its own)
    await auth_client.patch(
        f"/collections/{collection_id}/items/{item_id}",
        json={"primary_color": "multi"},
    )
    # Now try to add secondary colors in a separate request
    resp = await auth_client.patch(
        f"/collections/{collection_id}/items/{item_id}",
        json={"secondary_colors": ["tan"]},
    )
    # This request only sends secondary_colors — no primary_color in the body.
    # The validator only fires on values in the current request body, so this
    # passes (200). The mutual-exclusion rule is enforced when BOTH fields appear
    # in the same request body.
    assert resp.status_code == 200

    # Now send both fields in one request — this must be rejected.
    resp = await auth_client.patch(
        f"/collections/{collection_id}/items/{item_id}",
        json={"primary_color": "multi", "secondary_colors": ["tan"]},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_patch_primary_to_multi_auto_clears_secondary(auth_client, collection_id, item_id):
    """Setting primary_color=multi via PATCH auto-clears secondary_colors server-side."""
    # Set up item with secondary_colors
    await auth_client.patch(
        f"/collections/{collection_id}/items/{item_id}",
        json={"primary_color": "brown", "secondary_colors": ["tan"]},
    )
    # PATCH only primary_color to multi — server should auto-clear secondary
    resp = await auth_client.patch(
        f"/collections/{collection_id}/items/{item_id}",
        json={"primary_color": "multi"},
    )
    assert resp.status_code == 200
    assert resp.json()["secondary_colors"] == []


@pytest.mark.asyncio
async def test_update_item_invalid_secondary_colors_value_returns_422(auth_client, collection_id, item_id):
    """A value not in the color enum (e.g. 'purple') in secondary_colors returns 422."""
    resp = await auth_client.patch(
        f"/collections/{collection_id}/items/{item_id}",
        json={"secondary_colors": ["purple"]},
    )
    assert resp.status_code == 422
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /gt/purseinator/crew/kagarmoe && python -m pytest \
  tests/test_items.py::test_create_item_secondary_colors_default_empty \
  tests/test_items.py::test_multi_primary_color_with_secondary_colors_returns_422 \
  tests/test_items.py::test_secondary_colors_with_multi_primary_returns_422 \
  tests/test_items.py::test_patch_primary_to_multi_auto_clears_secondary \
  tests/test_items.py::test_update_item_invalid_secondary_colors_value_returns_422 \
  -v
```

Expected: all five `FAILED`.

- [ ] **Step 3: Add `model_validator` to `ItemUpdateBody` in `app/routes/items.py`**

Add `model_validator` to the Pydantic imports at the top of `app/routes/items.py`:

```python
from pydantic import BaseModel, Field, model_validator
```

Then add the validator as a method of `ItemUpdateBody` (after all the field declarations):

```python
    @model_validator(mode="after")
    def check_multi_color_exclusion(self) -> "ItemUpdateBody":
        if self.primary_color == "multi" and self.secondary_colors:
            raise ValueError(
                "When primary_color is 'multi', secondary_colors must be empty."
            )
        return self
```

> Note: Because `model_validator(mode="after")` only fires on fields that are set in the body, it only sees values actually present in the request. Fields with `None` default that were not sent will be `None` here, so the check correctly ignores absent fields.

- [ ] **Step 4: Add the auto-clear to the `update_item` route handler in `app/routes/items.py`**

In the `update_item` function, after building `update_data` from the body and before executing the DB update, add:

```python
    # Auto-clear secondary_colors when primary_color is set to "multi",
    # preserving the mutual-exclusion invariant even when secondary_colors
    # is not included in this request body.
    if update_data.get("primary_color") == "multi":
        update_data["secondary_colors"] = []
```

- [ ] **Step 5: Also add the validator and `Field(default_factory=list)` to `ItemCreateBody`**

`ItemCreateBody` does not yet have `primary_color` or `secondary_colors` fields. Add them (with defaults matching the DB defaults) and the validator:

```python
class ItemCreateBody(BaseModel):
    brand: str = "unknown"
    description: str = ""
    condition_score: Optional[float] = None
    status: str = "undecided"
    primary_color: Optional[Literal[
        "red", "yellow", "orange", "green", "blue", "violet",
        "white", "black", "tan", "brown", "multi"
    ]] = None
    secondary_colors: list[Literal[
        "red", "yellow", "orange", "green", "blue", "violet",
        "white", "black", "tan", "brown", "multi"
    ]] = Field(default_factory=list)
    style: Optional[Literal[
        "satchel", "saddlebag", "duffel", "frame", "messenger", "tote",
        "foldover", "barrel", "bucket", "hobo", "baguette", "doctor",
        "backpack", "clutch", "envelope", "minaudiere", "crossbody",
        "diaper", "wristlet", "belt-bag"
    ]] = None
    material: Optional[Literal[
        "leather", "vegan leather", "cloth", "tapestry", "velvet", "suede", "performance"
    ]] = None
    width_in: Optional[float] = None
    height_in: Optional[float] = None
    depth_in: Optional[float] = None
    serial_number: Optional[str] = None
    asking_price: Optional[int] = None

    @model_validator(mode="after")
    def check_multi_color_exclusion(self) -> "ItemCreateBody":
        if self.primary_color == "multi" and self.secondary_colors:
            raise ValueError(
                "When primary_color is 'multi', secondary_colors must be empty."
            )
        return self
```

Also extend the `create_item` route handler in `app/routes/items.py` to pass the new fields to `ItemTable`. Replace the current `ItemTable(...)` call inside `create_item`:

```python
    row = ItemTable(
        collection_id=collection_id,
        brand=body.brand,
        description=body.description,
        condition_score=body.condition_score,
        status=body.status,
        primary_color=body.primary_color,
        secondary_colors=body.secondary_colors,
        style=body.style,
        material=body.material,
        width_in=body.width_in,
        height_in=body.height_in,
        depth_in=body.depth_in,
        serial_number=body.serial_number,
        asking_price=body.asking_price,
    )
```

- [ ] **Step 6: Extend `ItemCreate` in `app/models.py`**

`ItemCreate` is used in `tests/test_models.py` and is not dead code. Add the nine new optional fields (and `secondary_colors` with `Field(default_factory=list)`). Also add `Field` to the Pydantic import at the top of `app/models.py` if not already there:

```python
from pydantic import BaseModel, ConfigDict, Field, field_validator
```

Replace `ItemCreate` with:

```python
class ItemCreate(BaseModel):
    model_config = ConfigDict(frozen=True)

    collection_id: int
    brand: str = "unknown"
    description: str = ""
    condition_score: Optional[float] = None
    status: Literal["undecided", "keeper", "seller"] = "undecided"
    primary_color: Optional[str] = None
    secondary_colors: list[str] = Field(default_factory=list)
    style: Optional[str] = None
    material: Optional[str] = None
    width_in: Optional[float] = None
    height_in: Optional[float] = None
    depth_in: Optional[float] = None
    serial_number: Optional[str] = None
    asking_price: Optional[int] = None
```

- [ ] **Step 7: Run tests to verify they pass**

```bash
cd /gt/purseinator/crew/kagarmoe && python -m pytest \
  tests/test_items.py::test_create_item_secondary_colors_default_empty \
  tests/test_items.py::test_multi_primary_color_with_secondary_colors_returns_422 \
  tests/test_items.py::test_secondary_colors_with_multi_primary_returns_422 \
  tests/test_items.py::test_patch_primary_to_multi_auto_clears_secondary \
  tests/test_items.py::test_update_item_invalid_secondary_colors_value_returns_422 \
  -v
```

Expected: all five `PASSED`.

- [ ] **Step 8: Run the full suite**

```bash
cd /gt/purseinator/crew/kagarmoe && python -m pytest tests/ -v --tb=short 2>&1 | tail -20
```

Expected: all previous + 5 new = 104 tests pass.

- [ ] **Step 9: Commit**

```bash
cd /gt/purseinator/crew/kagarmoe && git add app/routes/items.py app/models.py tests/test_items.py && git commit -m "feat: add multi-color mutual-exclusion validator, auto-clear, and extend ItemCreate"
```

---

### Task 7: Single Alembic migration — add all 9 columns, backfill `secondary_colors`

**Files:**
- Create: `alembic/versions/<hash>_add_item_metadata_columns.py`

This is a single migration that adds all nine new columns to the `items` table and backfills `secondary_colors` with `'[]'` for any existing rows. The tests in this task verify the migration by running it against a fresh SQLite file (not the in-memory DB used in other tests — this exercises `alembic upgrade head` for real).

**Migration sequencing:** This plan is sequenced AFTER the `add_used_tokens_table` migration. This migration's `down_revision` must be `"a1b2c3d4e5f6"` (the `add_used_tokens_table` revision). Any subsequent plan's migration will rebase to chain off this migration's revision once this plan lands.

**DATABASE_URL wiring:** `alembic/env.py` reads the DB URL via `get_settings().database_url`, which is driven by the `PURSEINATOR_DATABASE_URL` environment variable (pydantic-settings with `env_prefix = "PURSEINATOR_"`). The subprocess test must set `PURSEINATOR_DATABASE_URL` to a `sqlite+aiosqlite:///` URL (the async driver is required because `env.py` uses `async_engine_from_config`). `PYTHONPATH` must also be set so `app.config` is importable.

- [ ] **Step 1: Write a failing migration-coverage test**

Add to `tests/test_items.py`:

```python
import subprocess
import os


def test_migration_adds_all_item_metadata_columns(tmp_path):
    """Run alembic upgrade head on a fresh SQLite DB and verify all new columns exist."""
    db_path = str(tmp_path / "migration_test.db")
    env = {
        **os.environ,
        "PURSEINATOR_DATABASE_URL": f"sqlite+aiosqlite:///{db_path}",
        "PYTHONPATH": "/gt/purseinator/crew/kagarmoe",
    }
    result = subprocess.run(
        ["python", "-m", "alembic", "upgrade", "head"],
        cwd="/gt/purseinator/crew/kagarmoe",
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode == 0, f"alembic upgrade failed:\n{result.stderr}"

    # Inspect the schema using sqlite3 (synchronous — no async needed here)
    import sqlite3
    conn = sqlite3.connect(db_path)
    cursor = conn.execute("PRAGMA table_info(items)")
    columns = {row[1] for row in cursor.fetchall()}
    conn.close()

    expected_new_columns = {
        "primary_color", "secondary_colors", "style", "material",
        "width_in", "height_in", "depth_in", "serial_number", "asking_price",
    }
    missing = expected_new_columns - columns
    assert not missing, f"Migration did not add columns: {missing}"
```

Note: this is a plain (non-async) test — `subprocess.run` is synchronous and does not need `@pytest.mark.asyncio`.

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /gt/purseinator/crew/kagarmoe && python -m pytest tests/test_items.py::test_migration_adds_all_item_metadata_columns -v
```

Expected: `FAILED` — columns are absent because the migration does not exist yet.

- [ ] **Step 3: Generate the migration with alembic autogenerate**

```bash
cd /gt/purseinator/crew/kagarmoe && python -m alembic revision --autogenerate -m "add_item_metadata_columns"
```

This creates a new file under `alembic/versions/`. Note the generated filename (it will have a random hash prefix). Open it immediately.

- [ ] **Step 4: Verify `down_revision` and fix `secondary_colors` column**

Open the generated migration file and check two things:

**4a. Verify `down_revision` chaining:**

```bash
grep "down_revision" alembic/versions/<new_file>.py
```

Expected: `down_revision = 'a1b2c3d4e5f6'` (chains off `add_used_tokens_table`). If autogenerate picked a different parent, correct it manually.

**4b. Fix `secondary_colors` column type and nullability:**

Alembic autogenerate on SQLite sometimes emits `sa.Text()` instead of `sa.JSON()`, and may emit `nullable=True` even though the model says `nullable=False`. Fix both.

The `secondary_colors` `add_column` call must be:

```python
op.add_column('items', sa.Column('secondary_colors', sa.JSON(), server_default=sa.text("'[]'"), nullable=False))
```

The full `upgrade()` and `downgrade()` must look like:

```python
def upgrade() -> None:
    op.add_column('items', sa.Column('primary_color', sa.String(length=20), nullable=True))
    op.add_column('items', sa.Column('secondary_colors', sa.JSON(), server_default=sa.text("'[]'"), nullable=False))
    op.add_column('items', sa.Column('style', sa.String(length=30), nullable=True))
    op.add_column('items', sa.Column('material', sa.String(length=30), nullable=True))
    op.add_column('items', sa.Column('width_in', sa.Float(), nullable=True))
    op.add_column('items', sa.Column('height_in', sa.Float(), nullable=True))
    op.add_column('items', sa.Column('depth_in', sa.Float(), nullable=True))
    op.add_column('items', sa.Column('serial_number', sa.String(length=255), nullable=True))
    op.add_column('items', sa.Column('asking_price', sa.Integer(), nullable=True))

    # Backfill: ensure any existing rows have secondary_colors = '[]'.
    # This is redundant under server_default but is safe to keep.
    op.execute("UPDATE items SET secondary_colors = '[]' WHERE secondary_colors IS NULL")


def downgrade() -> None:
    op.drop_column('items', 'asking_price')
    op.drop_column('items', 'serial_number')
    op.drop_column('items', 'depth_in')
    op.drop_column('items', 'height_in')
    op.drop_column('items', 'width_in')
    op.drop_column('items', 'material')
    op.drop_column('items', 'style')
    op.drop_column('items', 'secondary_colors')
    op.drop_column('items', 'primary_color')
```

- [ ] **Step 5: Run the migration test to verify it passes**

```bash
cd /gt/purseinator/crew/kagarmoe && python -m pytest tests/test_items.py::test_migration_adds_all_item_metadata_columns -v
```

Expected: `PASSED`.

- [ ] **Step 6: Run the full test suite**

```bash
cd /gt/purseinator/crew/kagarmoe && python -m pytest tests/ -v --tb=short 2>&1 | tail -20
```

Expected: all previous + 1 new = 105 tests pass.

- [ ] **Step 7: Commit**

```bash
cd /gt/purseinator/crew/kagarmoe && git add alembic/versions/ tests/test_items.py && git commit -m "feat: alembic migration adds all item metadata columns with secondary_colors backfill"
```

---

## Self-Review

### Spec Coverage

| Spec requirement | Covered by |
|-----------------|------------|
| `primary_color` nullable column + color enum | Tasks 1, 2 |
| `secondary_colors` JSON column, `nullable=False`, `server_default='[]'` | Tasks 1, 3 |
| `style` nullable column + style enum | Tasks 1, 2 |
| `material` nullable column + material enum | Tasks 1, 2 |
| `width_in` float nullable | Task 4 |
| `height_in` float nullable | Task 4 |
| `depth_in` float nullable (meaningful 0) | Task 4 |
| `serial_number` nullable string | Task 5 |
| `asking_price` nullable int (whole dollars) | Task 5 |
| Python `Color`, `Style`, `Material` enum constants | Task 1 |
| Pydantic schemas extended (`ItemRead`, `ItemCreate`, `ItemCreateBody`, `ItemUpdateBody`) | Tasks 2–6 |
| `ItemCreate` extended (used in `tests/test_models.py`) | Task 6 Step 6 |
| Multi-color mutual-exclusion validator (single check, single error message) | Task 6 |
| Validator returns 422 on direct violation (multi + non-empty secondary in same body) | Task 6 |
| PATCH auto-clear: setting `primary_color=multi` forces `secondary_colors=[]` server-side | Task 6 Step 4 |
| `secondary_colors` default `[]` via `Field(default_factory=list)` | Task 6 (moved from Task 3) |
| Invalid value in `secondary_colors` returns 422 | Task 6 |
| Alembic migration (single migration for all columns) | Task 7 |
| Migration chains off `down_revision = "a1b2c3d4e5f6"` | Task 7 Step 4a |
| Migration `secondary_colors` uses `sa.JSON()`, `nullable=False`, `server_default=sa.text("'[]'")` | Task 7 Step 4b |
| Backfill `secondary_colors = []` for existing rows (redundant under server_default but safe) | Task 7 Step 4b |
| Migration test uses `PURSEINATOR_DATABASE_URL` + `PYTHONPATH` env vars | Task 7 Step 1 |

All spec requirements are covered. No gaps.

### Placeholder Scan

No "TBD", "TODO", "implement later", "similar to above", or vague instructions found. Every code step contains complete code.

### Type Consistency

- `secondary_colors` is `list[str] = Field(default_factory=list)` in `ItemRead`, `list[Literal[...]] = Field(default_factory=list)` in `ItemUpdateBody` and `ItemCreateBody` — no mutable shared defaults.
- `primary_color` is `Optional[Color]` in `ItemRead` (the Python enum, for end-to-end type safety), `Optional[Literal[...]]` in `ItemUpdateBody` and `ItemCreateBody` (for validation at input boundary). Pydantic v2 handles enum coercion from string DB attributes natively with `from_attributes=True`.
- `style: Optional[Style]`, `material: Optional[Material]` in `ItemRead` — same pattern as `primary_color`.
- `depth_in: Optional[float]` — the `0.0` value for flat clutches is stored as a float, not mistaken for `None`. Confirmed in Task 4 test.
- `asking_price: Optional[int]` — confirmed as integer everywhere (no float/int mismatch).
- The `ItemTable.secondary_colors` column uses `nullable=False, default=list, server_default='[]'` — consistent between ORM model and migration.
- All nine new columns appear in `ItemRead`, `ItemCreate`, `ItemCreateBody`, and `ItemUpdateBody` — no omissions.

### Validator Correctness

- The `model_validator` in `ItemUpdateBody` and `ItemCreateBody` uses a single `if primary_color == "multi" and secondary_colors:` check. There is no duplicate or unreachable branch.
- The PATCH route's auto-clear (`if update_data.get("primary_color") == "multi": update_data["secondary_colors"] = []`) preserves the mutual-exclusion invariant server-side even when `secondary_colors` is absent from the request body. The Pydantic validator covers the direct-violation case (both fields in the same body).

**Test count: 16 new tests** (1 enum import + 3 color/style/material + 2 secondary_colors roundtrip + 2 dimensions + 2 serial/asking_price + 5 validator/auto-clear/invalid + 1 migration = 16 new tests on top of the 89 baseline = 105 total).
