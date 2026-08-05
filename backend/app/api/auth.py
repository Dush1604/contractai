
"""
Contractor registration and login routes.

Access tokens are delivered as httpOnly, Secure, SameSite=strict cookies —
never in the JSON response body and never intended for localStorage. This
means client-side JavaScript can never read the token directly, which
closes off an entire class of XSS-driven token theft.
"""
from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.limiter import limiter
from app.core.security import create_token
from app.db.session import get_db
from app.schemas.auth import ContractorLogin, ContractorRegister, ContractorResponse
from app.services.auth_service import authenticate_contractor, register_contractor

router = APIRouter()
settings = get_settings()

COOKIE_NAME = "contractai_access_token"


def _set_auth_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        secure=settings.ENVIRONMENT == "production",
        samesite="strict",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )


@router.post("/register", response_model=ContractorResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(settings.RATE_LIMIT_AUTH)
async def register(
    request: Request,  # required by slowapi
    payload: ContractorRegister,
    db: Session = Depends(get_db),
):
    user = register_contractor(db, payload)
    return user


@router.post("/login", response_model=ContractorResponse)
@limiter.limit(settings.RATE_LIMIT_AUTH)
async def login(
    request: Request,  # required by slowapi
    payload: ContractorLogin,
    response: Response,
    db: Session = Depends(get_db),
):
    user = authenticate_contractor(db, payload.email, payload.password)
    token = create_token(subject=user.id, token_type="access")
    _set_auth_cookie(response, token)
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(response: Response):
    response.delete_cookie(key=COOKIE_NAME, path="/")
    