
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
from app.services.project_service import get_project_by_claim
router = APIRouter()
settings = get_settings()


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
    