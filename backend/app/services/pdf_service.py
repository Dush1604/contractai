
"""
Generates a downloadable estimate PDF for a project — combines the
homeowner's submission, AI analysis, scope of work, cost estimate, and
uploaded photos into a single client-ready document.
"""
import io
import json
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image as RLImage,
    Table, TableStyle, ListFlowable, ListItem,
)

from app.models.models import Project, ProjectAnalysis, EstimateResult, ProjectImage

styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name="SectionHeading", parent=styles["Heading2"], spaceBefore=16, spaceAfter=8))
styles.add(ParagraphStyle(name="Disclaimer", parent=styles["Normal"], fontSize=8, textColor=colors.grey))


def _bullet_list(items: list[str]) -> ListFlowable:
    return ListFlowable(
        [ListItem(Paragraph(item, styles["Normal"])) for item in items],
        bulletType="bullet",
        leftIndent=18,
    )


def generate_estimate_pdf(
    project: Project,
    analysis: ProjectAnalysis,
    estimate: EstimateResult,
    images: list[ProjectImage],
) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=letter,
        topMargin=0.75 * inch, bottomMargin=0.75 * inch,
        leftMargin=0.75 * inch, rightMargin=0.75 * inch,
    )

    story = []

    # --- Header ---
    story.append(Paragraph("ContractAI Estimate", styles["Title"]))
    story.append(Paragraph(f"Generated {datetime.utcnow().strftime('%B %d, %Y')}", styles["Normal"]))
    story.append(Spacer(1, 16))

    # --- Project summary ---
    story.append(Paragraph(project.title, styles["Heading1"]))
    summary_rows = [
        ["Homeowner", project.homeowner_name],
        ["Location", project.property_location or "Not provided"],
        ["Timeline", project.desired_timeline or "Not provided"],
    ]
    summary_table = Table(summary_rows, colWidths=[1.5 * inch, 4.5 * inch])
    summary_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 8))
    story.append(Paragraph(project.description, styles["Normal"]))

    # --- Classification ---
    story.append(Paragraph("Project Classification", styles["SectionHeading"]))
    story.append(Paragraph(f"<b>Category:</b> {analysis.category} &nbsp;&nbsp; <b>Complexity:</b> {analysis.complexity}", styles["Normal"]))

    # --- Scope of work ---
    story.append(Paragraph("Scope of Work", styles["SectionHeading"]))
    story.append(_bullet_list(json.loads(estimate.scope_of_work)))

    # --- Estimate ---
    story.append(Paragraph("Estimated Cost Range", styles["SectionHeading"]))
    estimate_text = f"${estimate.estimate_min:,.0f} &ndash; ${estimate.estimate_max:,.0f}"
    story.append(Paragraph(estimate_text, ParagraphStyle(
        name="EstimateAmount", parent=styles["Normal"], fontSize=18, leading=22,
        textColor=colors.HexColor("#1a7f37"), spaceAfter=6,
    )))
    story.append(Paragraph(f"Confidence: {estimate.confidence}", styles["Normal"]))

    # --- Assumptions ---
    story.append(Paragraph("Assumptions", styles["SectionHeading"]))
    story.append(_bullet_list(json.loads(estimate.assumptions)))

    # --- Risk factors ---
    story.append(Paragraph("Risk Factors", styles["SectionHeading"]))
    story.append(_bullet_list(json.loads(estimate.risk_factors)))

    # --- Photos ---
    if images:
        story.append(Paragraph("Submitted Photos", styles["SectionHeading"]))
        for image in images:
            try:
                rl_image = RLImage(image.storage_path, width=3 * inch, height=2.25 * inch, kind="proportional")
                caption = image.predicted_category or "Uncategorized"
                story.append(rl_image)
                story.append(Paragraph(caption, styles["Normal"]))
                story.append(Spacer(1, 8))
            except Exception:
                # A missing/corrupt file on disk shouldn't prevent the
                # rest of the PDF from generating — skip it and move on.
                continue

    # --- Disclaimer ---
    story.append(Spacer(1, 20))
    story.append(Paragraph(
        "This is a preliminary, AI-generated estimate based on the information and photos provided. "
        "Final pricing is subject to an in-person inspection and may vary based on site conditions, "
        "material selection, and other factors not visible from the submitted information.",
        styles["Disclaimer"],
    ))

    doc.build(story)
    return buffer.getvalue()
    