from __future__ import annotations

import typer

app = typer.Typer(name="bagfolio", help="Bagfolio CLI")


@app.command()
def serve(host: str = "0.0.0.0", port: int = 8000):
    """Start the Bagfolio API server."""
    import uvicorn

    uvicorn.run("bagfolio.main:create_app", factory=True, host=host, port=port)
