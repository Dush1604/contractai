
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
from app.ai.estimate_generation import run_estimate_generation
from app.api.deps import get_current_contractor
from app.db.session import get_db
from app.models.models import Project, ProjectAnalysis, User
from app.schemas.analysis import ProjectAnalysisResponse, EstimateResponse

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
        analysis = run_project_analysis(db, project)
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
        scope_of_work=json.loads(analysis.scope_of_work),
        model_version=analysis.model_version,
    )

@router.post("/{project_id}/estimate", response_model=EstimateResponse)
async def generate_estimate(
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

    analysis = db.query(ProjectAnalysis).filter(ProjectAnalysis.project_id == project.id).first()
    if analysis is None or not analysis.scope_of_work:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Run project analysis before generating an estimate.",
        )

    scope_of_work = json.loads(analysis.scope_of_work)

    try:
        estimate = run_estimate_generation(db, project, analysis, scope_of_work)
    except OpenAIError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI estimate generation is temporarily unavailable. Please try again.",
        )
    except (json.JSONDecodeError, KeyError):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI estimate generation returned an unexpected response. Please try again.",
        )

    return EstimateResponse(
        id=estimate.id,
        scope_of_work=json.loads(estimate.scope_of_work),
        estimate_min=estimate.estimate_min,
        estimate_max=estimate.estimate_max,
        confidence=estimate.confidence,
        assumptions=json.loads(estimate.assumptions),
        risk_factors=json.loads(estimate.risk_factors),
        approved_by_contractor=estimate.approved_by_contractor,
    )
