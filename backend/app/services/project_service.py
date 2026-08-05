
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
    