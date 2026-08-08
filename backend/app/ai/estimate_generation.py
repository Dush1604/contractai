
"""
LLM-powered cost estimate generation.

Takes a project's description plus its prior analysis (category,
complexity, scope of work) and produces a cost range with assumptions
and risk factors. Deliberately does NOT look at uploaded images — see
project notes on why image input is intentionally deferred to the
planned PyTorch classifier rather than fed directly to the LLM.
"""
import json

from openai import OpenAI
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.models import EstimateResult, Project, ProjectAnalysis

settings = get_settings()
client = OpenAI(api_key=settings.OPENAI_API_KEY)

ESTIMATE_MODEL = "gpt-4o"

SYSTEM_PROMPT = """You are an assistant helping a home-renovation contractor produce a rough, early-stage cost estimate for a homeowner's project lead.

You will be given the project description, its category, complexity, and a scope of work already prepared by another step. Using general US residential renovation cost knowledge, respond with ONLY a JSON object (no markdown, no commentary) with this exact shape:

{
  "estimate_min": <number, USD, lower bound of a realistic range>,
  "estimate_max": <number, USD, upper bound of a realistic range>,
  "confidence": "Low, Medium, or High — how confident this range is given how much information is available",
  "assumptions": ["specific assumptions this estimate relies on, e.g. materials, that a permit is not required, standard site conditions"],
  "risk_factors": ["specific things that could push the actual cost outside this range, e.g. hidden structural damage, permit costs, site access issues"]
}

Be conservative and realistic — this is a rough early estimate shown to a homeowner before any in-person inspection, not a final quote. If information is genuinely too sparse to estimate responsibly, set confidence to "Low" and keep the range wide rather than fabricating false precision."""


def run_estimate_generation(
    db: Session, project: Project, analysis: ProjectAnalysis, scope_of_work: list[str]
) -> EstimateResult:
    """Calls the LLM, parses its response, and upserts an EstimateResult
    row. Safe to call multiple times — replaces the previous estimate
    rather than duplicating it, mirroring run_project_analysis."""

    user_prompt = (
        f"Project title: {project.title}\n"
        f"Description: {project.description}\n"
        f"Category: {analysis.category}\n"
        f"Complexity: {analysis.complexity}\n"
        f"Scope of work:\n" + "\n".join(f"- {item}" for item in scope_of_work)
    )

    response = client.chat.completions.create(
        model=ESTIMATE_MODEL,
        max_tokens=800,
        temperature=0.3,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    )

    parsed = json.loads(response.choices[0].message.content)

    existing = db.query(EstimateResult).filter(EstimateResult.project_id == project.id).first()
    estimate = existing if existing else EstimateResult(project_id=project.id)
    if not existing:
        db.add(estimate)

    estimate.scope_of_work = json.dumps(scope_of_work)
    estimate.estimate_min = parsed.get("estimate_min")
    estimate.estimate_max = parsed.get("estimate_max")
    estimate.confidence = parsed.get("confidence")
    estimate.assumptions = json.dumps(parsed.get("assumptions", []))
    estimate.risk_factors = json.dumps(parsed.get("risk_factors", []))

    db.commit()
    db.refresh(estimate)

    return estimate
    