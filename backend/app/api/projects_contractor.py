
"""
Contractor-facing project routes — everything here requires a logged-in
contractor and is scoped to that contractor's own projects only.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_contractor
from app.db.session import get_db
from app.models.models import Project, User, ProjectImage
from app.schemas.project import ProjectListItem
from app.schemas.image import ProjectImageWithPrediction

router = APIRouter()


@router.get("/", response_model=list[ProjectListItem])
async def list_my_projects(
    contractor: User = Depends(get_current_contractor),
    db: Session = Depends(get_db),
):
    projects = (
        db.query(Project)
        .filter(Project.contractor_id == contractor.id)
        .order_by(Project.created_at.desc())
        .all()
    )
    return projects

@router.get("/{project_id}/images", response_model=list[ProjectImageWithPrediction])
async def list_project_images(
    project_id: str,
    contractor: User = Depends(get_current_contractor),
    db: Session = Depends(get_db),
):
    project = (
        db.query(Project)
        .filter(Project.id == project_id, Project.contractor_id == contractor.id)
        .first()
    )
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    images = db.query(ProjectImage).filter(ProjectImage.project_id == project_id).all()
    return images
    