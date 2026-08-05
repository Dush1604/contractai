
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

from jose import jwt, JWTError
from passlib.context import CryptContext

from app.core.config import get_settings

settings = get_settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ---------- Passwords ----------

def hash_password(plain_password: str) -> str:
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


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
    