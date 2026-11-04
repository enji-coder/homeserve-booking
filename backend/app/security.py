import os
import time
import uuid
from datetime import datetime, timedelta

import bcrypt
import jwt
from fastapi import HTTPException

SECRET = os.getenv("JWT_SECRET", "homeserve-dev-change-me")
ALGO = "HS256"
REVOKED: set[str] = set()
_HITS: dict[str, list[float]] = {}


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except Exception:
        return False


def create_token(user_id: int, role: str) -> str:
    payload = {
        "sub": str(user_id),
        "role": role,
        "jti": uuid.uuid4().hex,
        "exp": datetime.utcnow() + timedelta(hours=12),
    }
    return jwt.encode(payload, SECRET, algorithm=ALGO)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET, algorithms=[ALGO])
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Session expired. Please login again.")


def rate_limit(key: str, limit: int = 30, window: int = 60) -> None:
    now = time.time()
    hits = [stamp for stamp in _HITS.get(key, []) if now - stamp < window]
    if len(hits) >= limit:
        raise HTTPException(status_code=429, detail="Too many attempts. Please wait a minute and try again.")
    hits.append(now)
    _HITS[key] = hits
