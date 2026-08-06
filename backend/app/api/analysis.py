
"""
On-demand AI analysis endpoint — contractor-triggered, not automatic.
See the module docstring in app.ai.scope_generation for why the actual
analysis logic is deliberately kept separate from this trigger.
"""
import json

from fastapi import APIRouter, Depends, HTTPException, status
from openai import OpenAIError
from sqlalchemy.orm import Session

from app.ai.scope_generation import run_project_analysis
from app.api.deps import get_current_contractor
from app.db.session import get_db
from app.models.models import Project, User
from app.schemas.analysis import ProjectAnalysisResponse

router = APIRouter()


@router.post("/{project_id}/analyze", response_model=ProjectAnalysisResponse)
async def analyze_project(
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
        # Same principle as every other lookup in this app: a contractor
        # trying project IDs that aren't theirs gets a 404, not a 403 —
        # don't confirm the project exists at all if it isn't theirs.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    try:
        analysis, scope_of_work = run_project_analysis(db, project)
    except OpenAIError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI analysis is temporarily unavailable. Please try again.",
        )
    except (json.JSONDecodeError, KeyError):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI analysis returned an unexpected response. Please try again.",
        )

    return ProjectAnalysisResponse(
        id=analysis.id,
        category=analysis.category,
        complexity=analysis.complexity,
        missing_info=json.loads(analysis.missing_info),
        follow_up_questions=json.loads(analysis.follow_up_questions),
        scope_of_work=scope_of_work,
        model_version=analysis.model_version,
    )
    