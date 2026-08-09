
"""
PDF export endpoint — contractor-triggered, requires analysis and
estimate to already exist for the project.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_contractor
from app.db.session import get_db
from app.models.models import Project, ProjectAnalysis, EstimateResult, ProjectImage, User
from app.services.pdf_service import generate_estimate_pdf

router = APIRouter()


@router.get("/{project_id}/export-pdf")
async def export_project_pdf(
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
    estimate = db.query(EstimateResult).filter(EstimateResult.project_id == project.id).first()

    if analysis is None or estimate is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Run analysis and generate an estimate before exporting a PDF.",
        )

    images = db.query(ProjectImage).filter(ProjectImage.project_id == project.id).all()

    pdf_bytes = generate_estimate_pdf(project, analysis, estimate, images)

    safe_filename = project.title.replace(" ", "_").replace("/", "-")
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{safe_filename}_estimate.pdf"'},
    )
    