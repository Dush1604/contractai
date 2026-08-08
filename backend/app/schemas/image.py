
"""Pydantic schema for image upload responses."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ProjectImageResponse(BaseModel):
    id: str
    original_filename: str
    content_type: str
    size_bytes: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ProjectImageWithPrediction(BaseModel):
    id: str
    original_filename: str
    predicted_category: str | None
    predicted_confidence: float | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
