from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import jwt


def create_magic_token(email: str, secret: str, expiry_minutes: int = 15) -> str:
    payload = {
        "jti": str(uuid.uuid4()),
        "email": email,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=expiry_minutes),
        "type": "magic_link",
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def verify_magic_token(token: str, secret: str) -> tuple[str, str] | None:
    try:
        payload = jwt.decode(token, secret, algorithms=["HS256"])
        if payload.get("type") != "magic_link":
            return None
        email = payload.get("email")
        jti = payload.get("jti")
        if not email or not jti:
            return None
        return email, jti
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None


def create_session_id() -> str:
    return str(uuid.uuid4())
