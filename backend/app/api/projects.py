
"""
Public project intake endpoint.

This is deliberately unauthenticated — homeowners have no accounts. Trust
boundary is enforced by: strict input validation, per-route rate limiting,
and verifying the target contractor actually exists before creating
anything tied to them.
"""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.limiter import limiter
from app.db.session import get_db
from app.models.models import User, UserRole
from app.schemas.project import ProjectCreate, ProjectCreateResponse
from app.services.project_service import create_project

router = APIRouter()
settings = get_settings()


@router.post(
    "/{contractor_id}",
    response_model=ProjectCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit(settings.RATE_LIMIT_INTAKE)
async def submit_project(
    request: Request,  # required by slowapi's limiter, even though unused directly
    contractor_id: str,
    payload: ProjectCreate,
    db: Session = Depends(get_db),
):
    contractor = (
        db.query(User)
        .filter(User.id == contractor_id, User.role == UserRole.contractor, User.is_active.is_(True))
        .first()
    )
    if contractor is None:
        # Deliberately vague — do not reveal whether the ID is malformed,
        # belongs to a non-contractor, or simply doesn't exist. Any of
        # those distinctions would help an attacker enumerate valid IDs.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contractor not found")

    project = create_project(db=db, contractor_id=contractor_id, payload=payload)
    return project

from app.schemas.project import ProjectStatusResponse
from app.services.project_service import get_project_by_claim


@router.get("/{project_id}/status", response_model=ProjectStatusResponse)
async def get_project_status(
    project_id: str,
    claim_token: str,
    db: Session = Depends(get_db),
):
    return get_project_by_claim(db, project_id, claim_token)
