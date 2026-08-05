
"""
Auth primitives.

- Contractor accounts: bcrypt-hashed passwords + short-lived JWT access
  tokens delivered as httpOnly cookies, with a longer-lived refresh token.
- Homeowners: no password. They get a single-purpose, cryptographically
  random "claim link" token (not a guessable/sequential project id) that
  expires after CLAIM_LINK_EXPIRE_DAYS.
"""
import secrets
from datetime import datetime, timedelta, timezone
from typing import Literal

import bcrypt
from jose import jwt, JWTError

from app.core.config import get_settings

settings = get_settings()


# ---------- Passwords ----------

def hash_password(plain_password: str) -> str:
    # bcrypt operates on bytes and has a hard 72-byte input limit — our
    # schema's max_length=128 (characters) could exceed that in bytes for
    # non-ASCII input, so we truncate defensively rather than let bcrypt
    # raise. This mirrors what passlib was silently handling for us.
    password_bytes = plain_password.encode("utf-8")[:72]
    hashed = bcrypt.hashpw(password_bytes, bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    password_bytes = plain_password.encode("utf-8")[:72]
    return bcrypt.checkpw(password_bytes, hashed_password.encode("utf-8"))


# ---------- JWT (contractor auth) ----------

def create_token(subject: str, token_type: Literal["access", "refresh"]) -> str:
    now = datetime.now(timezone.utc)
    if token_type == "access":
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    else:
        expire = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    payload = {"sub": subject, "type": token_type, "iat": now, "exp": expire}
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        return None


# ---------- Claim links (homeowner access, no password) ----------

def generate_claim_token() -> str:
    """URL-safe, high-entropy token. Not derived from project id — must be
    looked up, not guessed or enumerated."""
    return secrets.token_urlsafe(32)


def claim_token_expiry() -> datetime:
    return datetime.utcnow() + timedelta(days=settings.CLAIM_LINK_EXPIRE_DAYS)
    