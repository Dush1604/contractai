
from pydantic import BaseModel, ConfigDict


class ProjectAnalysisResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    id: str
    category: str | None
    complexity: str | None
    missing_info: list[str]
    follow_up_questions: list[str]
    scope_of_work: list[str]
    model_version: str | None

class EstimateResponse(BaseModel):
    id: str
    scope_of_work: list[str]
    estimate_min: float | None
    estimate_max: float | None
    confidence: str | None
    assumptions: list[str]
    risk_factors: list[str]
    approved_by_contractor: bool
