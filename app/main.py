from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.routes import auth, collections, items, photos, ranking, upload

_MAX_REQUEST_BODY_BYTES = 200 * 1024 * 1024  # 200 MB


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Reject requests with Content-Length > 200 MB before reading the body."""

    async def dispatch(self, request: Request, call_next):
        cl = request.headers.get("content-length")
        if cl is not None:
            try:
                if int(cl) > _MAX_REQUEST_BODY_BYTES:
                    return JSONResponse(
                        status_code=413,
                        content={"detail": "Request body too large; maximum is 200 MB."},
                    )
            except ValueError:
                pass
        return await call_next(request)


def create_app(session_factory=None, photo_storage_root=None) -> FastAPI:
    from app.config import get_settings
    from app.database import get_session_factory
    from app.tasks.staging_cleanup import _cleanup_loop

    settings = get_settings()
    _session_factory = session_factory or get_session_factory()
    _storage_root = photo_storage_root or str(settings.photo_storage_root)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Start background cleanup task
        task = asyncio.create_task(_cleanup_loop(_session_factory, _storage_root))
        yield
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    app = FastAPI(title="Purseinator", version="0.1.0", lifespan=lifespan)

    # 200 MB per-request cap (checked via Content-Length header)
    app.add_middleware(RequestSizeLimitMiddleware)

    app.state.session_factory = _session_factory
    app.state.photo_storage_root = _storage_root

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    app.include_router(auth.router, prefix="/auth")
    app.include_router(collections.router, prefix="/collections")
    app.include_router(items.router, prefix="/collections/{collection_id}/items")
    app.include_router(photos.router)
    app.include_router(ranking.router, prefix="/collections/{collection_id}/ranking")
    app.include_router(upload.router, prefix="/upload")

    return app
