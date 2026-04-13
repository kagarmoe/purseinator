from __future__ import annotations

from fastapi import FastAPI

from bagfolio.routes import auth, collections, items, photos


def create_app(session_factory=None, photo_storage_root=None) -> FastAPI:
    from bagfolio.config import get_settings
    from bagfolio.database import get_session_factory

    settings = get_settings()
    app = FastAPI(title="Bagfolio", version="0.1.0")

    app.state.session_factory = session_factory or get_session_factory()
    app.state.photo_storage_root = photo_storage_root or str(settings.photo_storage_root)

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    app.include_router(auth.router, prefix="/auth")
    app.include_router(collections.router, prefix="/collections")
    app.include_router(items.router, prefix="/collections/{collection_id}/items")
    app.include_router(photos.router)

    return app
