from __future__ import annotations

from pathlib import Path


async def push_collection(
    client,
    manifest: dict,
    collection_name: str,
) -> dict:
    source_dir = Path(manifest["source_dir"])

    resp = await client.post("/collections", json={"name": collection_name})
    resp.raise_for_status()
    collection_id = resp.json()["id"]

    items_created = 0
    photos_uploaded = 0

    for group in manifest["groups"]:
        resp = await client.post(
            f"/collections/{collection_id}/items", json={"brand": "unknown"}
        )
        resp.raise_for_status()
        item_id = resp.json()["id"]
        items_created += 1

        for photo_name in group["photos"]:
            photo_path = source_dir / photo_name
            data = photo_path.read_bytes()
            resp = await client.post(
                f"/collections/{collection_id}/items/{item_id}/photos",
                files={"file": (photo_name, data, "image/jpeg")},
            )
            resp.raise_for_status()
            photos_uploaded += 1

    return {
        "collection_id": collection_id,
        "items_created": items_created,
        "photos_uploaded": photos_uploaded,
    }
