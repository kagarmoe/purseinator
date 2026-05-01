from __future__ import annotations

from datetime import datetime, timezone

from fastapi import Cookie, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import SessionTable, UserTable


async def get_db(request: Request):
    session_factory = request.app.state.session_factory
    async with session_factory() as session:
        yield session


async def get_photo_storage_root(request: Request) -> str:
    return request.app.state.photo_storage_root


async def get_current_user(
    session_id: str = Cookie(None),
    db: AsyncSession = Depends(get_db),
) -> UserTable:
    if not session_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    result = await db.execute(
        select(SessionTable).where(
            SessionTable.session_id == session_id,
            SessionTable.expires_at > datetime.now(timezone.utc),
        )
    )
    session = result.scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=401, detail="Invalid or expired session")

    result = await db.execute(select(UserTable).where(UserTable.id == session.user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")

    return user
