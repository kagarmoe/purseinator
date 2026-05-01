from fastapi import FastAPI

from app.main import create_app

# Mount the purseinator app at /api so Vercel's /api/* routing matches FastAPI's routes
_inner = create_app()
app = FastAPI()
app.mount("/api", _inner)
