from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Cookie, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from purseinator.auth import create_magic_token, create_session_id, verify_magic_token
from purseinator.config import get_settings
from purseinator.deps import get_current_user, get_db
from purseinator.models import SessionTable, UserTable

router = APIRouter()


class MagicLinkRequest(BaseModel):
    email: str


@router.post("/magic-link")
async def request_magic_link(body: MagicLinkRequest, db: AsyncSession = Depends(get_db)):
    settings = get_settings()
    token = create_magic_token(body.email, settings.secret_key, settings.magic_link_expiry_minutes)
    return {"token": token}


@router.get("/verify")
async def verify(token: str, db: AsyncSession = Depends(get_db)):
    settings = get_settings()
    email = verify_magic_token(token, settings.secret_key)
    if email is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    result = await db.execute(select(UserTable).where(UserTable.email == email))
    user = result.scalar_one_or_none()
    if user is None:
        user = UserTable(email=email, name=email.split("@")[0], role="curator")
        db.add(user)
        await db.flush()

    sid = create_session_id()
    session = SessionTable(
        session_id=sid,
        user_id=user.id,
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.session_expiry_days),
    )
    db.add(session)
    await db.commit()

    return {"session_id": sid, "email": email}


@router.get("/me")
async def me(user: UserTable = Depends(get_current_user)):
    return {"id": user.id, "email": user.email, "name": user.name, "role": user.role}


@router.post("/dev-login")
async def dev_login(db: AsyncSession = Depends(get_db)):
    settings = get_settings()
    if not settings.dev_mode:
        raise HTTPException(status_code=404, detail="Not found")

    email = "dev@purseinator.local"
    result = await db.execute(select(UserTable).where(UserTable.email == email))
    user = result.scalar_one_or_none()
    if user is None:
        user = UserTable(email=email, name="Dev User", role="operator")
        db.add(user)
        await db.flush()

    sid = create_session_id()
    session = SessionTable(
        session_id=sid,
        user_id=user.id,
        expires_at=datetime.now(timezone.utc) + timedelta(days=365),
    )
    db.add(session)
    await db.commit()

    return {"session_id": sid, "email": email, "name": user.name, "role": user.role}


@router.post("/logout")
async def logout(session_id: str = Cookie(None), db: AsyncSession = Depends(get_db)):
    if session_id:
        result = await db.execute(
            select(SessionTable).where(SessionTable.session_id == session_id)
        )
        session = result.scalar_one_or_none()
        if session:
            await db.delete(session)
            await db.commit()
    return {"status": "ok"}
