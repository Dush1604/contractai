
from pydantic import BaseModel, ConfigDict


class ProjectAnalysisResponse(BaseModel):
    id: str
    category: str | None
    complexity: str | None
    missing_info: list[str]
    follow_up_questions: list[str]
    scope_of_work: list[str]
    model_version: str | None
