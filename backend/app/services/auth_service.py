
"""
Contractor registration and login logic.

Login is the most security-sensitive function in the app: it's the primary
target for credential-stuffing and brute-force attacks. The lockout logic
here is a deliberate second layer of defense on top of the per-IP rate
limiting already applied at the route level — rate limiting alone isn't
enough, since it's IP-based and can be bypassed with proxy rotation, while
account lockout protects a specific account regardless of where the
requests come from.
"""
from datetime import datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models.models import User, UserRole
from app.schemas.auth import ContractorRegister

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 15


def register_contractor(db: Session, payload: ContractorRegister) -> User:
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing is not None:
        # Same email enumeration concern as before: don't say "email
        # already registered" vs "something else went wrong" — a generic
        # message prevents an attacker from using this endpoint to check
        # which emails have accounts.
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to register with the provided details.",
        )

    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=UserRole.contractor,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_contractor(db: Session, email: str, password: str) -> User:
    """Verifies credentials and enforces account lockout. Raises
    HTTPException on any failure — malformed input, wrong password,
    locked account, or nonexistent user all produce the same generic
    401, so none of those states are distinguishable from outside."""

    generic_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid email or password.",
    )

    user = db.query(User).filter(User.email == email).first()
    if user is None or not user.is_active:
        raise generic_error

    if user.locked_until and user.locked_until > datetime.utcnow():
        # Deliberately still a generic message, not "account locked" —
        # revealing lockout state to an unauthenticated caller confirms
        # the email is valid and recently under attack, which is itself
        # useful information to withhold.
        raise generic_error

    if not verify_password(password, user.password_hash):
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= MAX_FAILED_ATTEMPTS:
            user.locked_until = datetime.utcnow() + timedelta(minutes=LOCKOUT_DURATION_MINUTES)
        db.commit()
        raise generic_error

    # Successful login resets the counter — a genuine login should wipe
    # out any prior failed attempts, so an occasional typo doesn't creep
    # someone toward lockout over unrelated, spaced-out sessions.
    user.failed_login_attempts = 0
    user.locked_until = None
    db.commit()

    return user
    