from __future__ import annotations

import pytest


def test_enum_constants_importable():
    from app.models import Color, Style, Material
    assert Color.RED == "red"
    assert Color.MULTI == "multi"
    assert Style.SATCHEL == "satchel"
    assert Style.BELT_BAG == "belt-bag"
    assert Material.LEATHER == "leather"
    assert Material.VEGAN_LEATHER == "vegan leather"


@pytest.fixture
async def collection_id(auth_client):
    resp = await auth_client.post("/collections", json={"name": "Test Collection"})
    return resp.json()["id"]


@pytest.fixture
async def item_id(auth_client, collection_id):
    resp = await auth_client.post(
        f"/collections/{collection_id}/items", json={"brand": "Coach"}
    )
    return resp.json()["id"]


@pytest.mark.asyncio
async def test_create_item(auth_client, collection_id):
    resp = await auth_client.post(
        f"/collections/{collection_id}/items",
        json={"brand": "Coach", "status": "undecided"},
    )
    assert resp.status_code == 201
    assert resp.json()["brand"] == "Coach"


@pytest.mark.asyncio
async def test_create_item_unknown_brand(auth_client, collection_id):
    resp = await auth_client.post(
        f"/collections/{collection_id}/items", json={"brand": "unknown"}
    )
    assert resp.status_code == 201
    assert resp.json()["brand"] == "unknown"


@pytest.mark.asyncio
async def test_create_item_defaults(auth_client, collection_id):
    resp = await auth_client.post(f"/collections/{collection_id}/items", json={})
    assert resp.status_code == 201
    data = resp.json()
    assert data["brand"] == "unknown"
    assert data["status"] == "undecided"


@pytest.mark.asyncio
async def test_update_item_brand(auth_client, collection_id, item_id):
    resp = await auth_client.patch(
        f"/collections/{collection_id}/items/{item_id}",
        json={"brand": "Louis Vuitton"},
    )
    assert resp.status_code == 200
    assert resp.json()["brand"] == "Louis Vuitton"


@pytest.mark.asyncio
async def test_update_item_status(auth_client, collection_id, item_id):
    resp = await auth_client.patch(
        f"/collections/{collection_id}/items/{item_id}",
        json={"status": "keeper"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "keeper"


@pytest.mark.asyncio
async def test_list_items(auth_client, collection_id):
    await auth_client.post(f"/collections/{collection_id}/items", json={"brand": "A"})
    await auth_client.post(f"/collections/{collection_id}/items", json={"brand": "B"})
    resp = await auth_client.get(f"/collections/{collection_id}/items")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


@pytest.mark.asyncio
async def test_get_item(auth_client, collection_id, item_id):
    resp = await auth_client.get(f"/collections/{collection_id}/items/{item_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == item_id


@pytest.mark.asyncio
async def test_get_item_not_found(auth_client, collection_id):
    resp = await auth_client.get(f"/collections/{collection_id}/items/999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_patch_item_non_owner_returns_403(auth_client, other_auth_client, collection_id, item_id):
    resp = await other_auth_client.patch(
        f"/collections/{collection_id}/items/{item_id}",
        json={"brand": "Gucci"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_list_items_non_owner_returns_403(auth_client, other_auth_client, collection_id, item_id):
    resp = await other_auth_client.get(f"/collections/{collection_id}/items")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_get_item_non_owner_returns_403(auth_client, other_auth_client, collection_id, item_id):
    resp = await other_auth_client.get(f"/collections/{collection_id}/items/{item_id}")
    assert resp.status_code == 403


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
async def test_setting_secondary_after_primary_is_multi_returns_422(auth_client, collection_id, item_id):
    # Set primary to multi (auto-clears secondary)
    resp1 = await auth_client.patch(
        f"/collections/{collection_id}/items/{item_id}",
        json={"primary_color": "multi", "secondary_colors": []},
    )
    assert resp1.status_code == 200
    # Now try to set secondary while primary is multi — must 422
    resp2 = await auth_client.patch(
        f"/collections/{collection_id}/items/{item_id}",
        json={"secondary_colors": ["tan"]},
    )
    assert resp2.status_code == 422


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
        ["python3", "-m", "alembic", "upgrade", "head"],
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
