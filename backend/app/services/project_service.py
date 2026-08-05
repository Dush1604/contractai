
"""
Business logic for project creation and lookup.

Kept separate from the API route so the logic isn't tangled up with
HTTP-specific concerns (status codes, request parsing) and can be tested
or reused independently.
"""
from sqlalchemy.orm import Session

from app.core.security import generate_claim_token, claim_token_expiry
from app.models.models import Project
from app.schemas.project import ProjectCreate


def create_project(db: Session, contractor_id: str, payload: ProjectCreate) -> Project:
    """Creates a new project tied to a specific contractor, with a fresh
    claim token the homeowner will use to check status later."""

    project = Project(
        contractor_id=contractor_id,
        title=payload.title,
        description=payload.description,
        homeowner_name=payload.homeowner_name,
        homeowner_email=payload.homeowner_email,
        homeowner_phone=payload.homeowner_phone,
        property_location=payload.property_location,
        desired_timeline=payload.desired_timeline,
        budget_range=payload.budget_range,
        claim_token=generate_claim_token(),
        claim_token_expires_at=claim_token_expiry(),
    )

    db.add(project)
    db.commit()
    db.refresh(project)

    return project

from datetime import datetime

from fastapi import HTTPException, status

def get_project_by_claim(db: Session, project_id: str, claim_token: str) -> Project:
    """Shared claim-token lookup used by any homeowner-facing route
    (image upload, status check, future ones) — one place to change the
    validation logic instead of duplicating it per route."""

    project = (
        db.query(Project)
        .filter(Project.id == project_id, Project.claim_token == claim_token)
        .first()
    )
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    if project.claim_token_expires_at < datetime.utcnow():
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="This link has expired")

    return project
