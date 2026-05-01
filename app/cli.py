from __future__ import annotations

import json
from pathlib import Path

import typer

app = typer.Typer(name="purseinator", help="Purseinator CLI")


@app.command()
def serve(host: str = "0.0.0.0", port: int = 8000):
    """Start the Purseinator API server."""
    import uvicorn

    uvicorn.run("app.main:create_app", factory=True, host=host, port=port)


@app.command()
def ingest(
    photo_dir: str = typer.Argument(..., help="Directory of photos from SD card dump"),
    output: str = typer.Option("manifest.json", help="Output manifest file path"),
):
    """Ingest photos from SD card dump. Splits on neon green card delimiter."""
    import cv2

    from app.ingest.card_detector import is_delimiter_card
    from app.ingest.grouper import group_photos

    photo_path = Path(photo_dir)
    extensions = {".jpg", ".jpeg", ".png", ".tiff", ".tif"}
    files = sorted(
        f for f in photo_path.iterdir()
        if f.is_file() and f.suffix.lower() in extensions
    )

    if not files:
        typer.echo(f"No image files found in {photo_dir}")
        raise typer.Exit(1)

    typer.echo(f"Scanning {len(files)} images...")

    card_flags = []
    for f in files:
        image = cv2.imread(str(f))
        if image is None:
            card_flags.append(False)
            continue
        card_flags.append(is_delimiter_card(image))

    filenames = [f.name for f in files]
    groups = group_photos(filenames, card_flags)

    manifest = {
        "source_dir": str(photo_path.resolve()),
        "groups": [{"photos": g} for g in groups],
    }

    Path(output).write_text(json.dumps(manifest, indent=2))

    cards_found = sum(card_flags)
    typer.echo(f"Found {cards_found} delimiter cards")
    typer.echo(f"Created {len(groups)} item groups ({sum(len(g) for g in groups)} photos)")
    typer.echo(f"Manifest written to {output}")


@app.command()
def push(
    manifest_path: str = typer.Argument(..., help="Path to ingest manifest JSON"),
    collection_name: str = typer.Option(..., help="Name for the collection"),
    server_url: str = typer.Option("http://localhost:8000", help="Purseinator server URL"),
    session_id: str = typer.Option(..., envvar="PURSEINATOR_SESSION_ID", help="Auth session ID"),
):
    """Push ingested photos to the Purseinator server."""
    import asyncio

    import httpx

    from app.cli_client import push_collection

    manifest = json.loads(Path(manifest_path).read_text())

    async def _push():
        async with httpx.AsyncClient(base_url=server_url) as client:
            client.cookies.set("session_id", session_id)
            return await push_collection(client, manifest, collection_name)

    result = asyncio.run(_push())
    typer.echo(f"Created {result['items_created']} items, uploaded {result['photos_uploaded']} photos")
