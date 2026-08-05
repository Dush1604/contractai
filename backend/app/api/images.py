
"""
Image upload endpoint.

Access control: homeowners have no accounts, so the claim_token (returned
at project creation) is the credential proving "I own this project." This
is the same claim-token pattern used for status lookups.
"""
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.limiter import limiter
from app.db.session import get_db
from app.models.models import Project
from app.schemas.image import ProjectImageResponse
from app.services.image_service import save_project_image

router = APIRouter()
settings = get_settings()


def _get_project_or_404_by_claim(db: Session, project_id: str, claim_token: str) -> Project:
    project = (
        db.query(Project)
        .filter(Project.id == project_id, Project.claim_token == claim_token)
        .first()
    )
    if project is None:
        # Same deliberately vague pattern as the contractor lookup — don't
        # reveal whether the project id is wrong, the token is wrong, or
        # both. Any distinction helps an attacker narrow down guesses.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    from datetime import datetime, timezone
    if project.claim_token_expires_at < datetime.utcnow():
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="This link has expired")

    return project


@router.post(
    "/{project_id}/images",
    response_model=ProjectImageResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit(settings.RATE_LIMIT_INTAKE)
async def upload_project_image(
    request: Request,  # required by slowapi
    project_id: str,
    claim_token: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    project = _get_project_or_404_by_claim(db, project_id, claim_token)
    image = save_project_image(db=db, project=project, upload=file)
    return image
    