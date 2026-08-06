
"""
LLM-powered project analysis: follow-up questions and scope of work.

Deliberately trigger-agnostic — this module only knows how to take a
project and produce analysis. It doesn't know or care whether it's called
from an on-demand contractor button click or an automatic post-intake
hook. That decision lives entirely in the route layer.
"""
import json

from openai import OpenAI
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.models import Project, ProjectAnalysis

settings = get_settings()
client = OpenAI(api_key=settings.OPENAI_API_KEY)

ANALYSIS_MODEL = "gpt-4o"

SYSTEM_PROMPT = """You are an assistant helping a home-renovation contractor triage incoming project leads.

Given a homeowner's project title and description, respond with ONLY a JSON object (no markdown, no commentary) with this exact shape:

{
  "category": "one of: Deck, Fence, Roofing, Flooring, Drywall, Landscaping, Kitchen, Bathroom, Other",
  "complexity": "Low, Medium, or High",
  "missing_info": ["short list of specific information a contractor would need but wasn't provided"],
  "follow_up_questions": ["specific, homeowner-facing questions to fill the gaps above"],
  "scope_of_work": ["ordered list of concrete work items a contractor would need to perform"]
}

Be specific and grounded in what's actually described — do not invent details not implied by the input. If the description already covers something (e.g. materials, dimensions), do not ask about it again."""


def run_project_analysis(db: Session, project: Project) -> ProjectAnalysis:
    """Calls the LLM, parses its response, and upserts a ProjectAnalysis
    row for the given project. Safe to call multiple times — re-running
    replaces the previous analysis rather than duplicating it."""

    user_prompt = f"Project title: {project.title}\n\nDescription: {project.description}"

    response = client.chat.completions.create(
        model=ANALYSIS_MODEL,
        max_tokens=800,
        temperature=0.3,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    )

    raw_content = response.choices[0].message.content
    parsed = json.loads(raw_content)

    existing = db.query(ProjectAnalysis).filter(ProjectAnalysis.project_id == project.id).first()

    if existing:
        analysis = existing
    else:
        analysis = ProjectAnalysis(project_id=project.id)
        db.add(analysis)

    analysis.category = parsed.get("category")
    analysis.complexity = parsed.get("complexity")
    analysis.missing_info = json.dumps(parsed.get("missing_info", []))
    analysis.follow_up_questions = json.dumps(parsed.get("follow_up_questions", []))
    analysis.model_version = ANALYSIS_MODEL

    db.commit()
    db.refresh(analysis)

    return analysis, parsed.get("scope_of_work", [])
    