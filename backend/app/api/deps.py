
"""
Shared FastAPI dependencies for authenticated routes.

get_current_contractor is the enforcement point for "only see your own
data" — every contractor-facing route that touches project data should
depend on this, not just check auth exists but resolve exactly which
contractor is asking.
"""
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.security import decode_token
from app.db.session import get_db
from app.models.models import User, UserRole

COOKIE_NAME = "contractai_access_token"


def get_current_contractor(request: Request, db: Session = Depends(get_db)) -> User:
    token = request.cookies.get(COOKIE_NAME)
    if token is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    payload = decode_token(token)
    if payload is None or payload.get("type") != "access":
        # Covers expired tokens, tampered tokens, and someone trying to
        # use a refresh token where an access token is required.
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == user_id).first()

    if user is None or not user.is_active or user.role != UserRole.contractor:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    return user
