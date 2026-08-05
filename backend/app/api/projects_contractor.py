
"""
Contractor-facing project routes — everything here requires a logged-in
contractor and is scoped to that contractor's own projects only.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_contractor
from app.db.session import get_db
from app.models.models import Project, User
from app.schemas.project import ProjectListItem

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
    