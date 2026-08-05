
"""
Pydantic schemas for project intake.

These define exactly what shape of data we accept from the public internet
and exactly what shape we send back — nothing more. Pydantic rejects
anything that doesn't match, which is our first line of defense against
malformed or malicious input.
"""
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, ConfigDict


class ProjectCreate(BaseModel):
    """What a homeowner submits via the public intake form."""

    model_config = ConfigDict(extra="forbid")  # reject unknown fields outright

    title: str = Field(..., min_length=3, max_length=200)
    description: str = Field(..., min_length=10, max_length=5000)

    homeowner_name: str = Field(..., min_length=1, max_length=200)
    homeowner_email: EmailStr
    homeowner_phone: str | None = Field(default=None, max_length=30)

    property_location: str | None = Field(default=None, max_length=300)
    desired_timeline: str | None = Field(default=None, max_length=200)
    budget_range: str | None = Field(default=None, max_length=100)


class ProjectCreateResponse(BaseModel):
    """What we hand back after a successful submission — enough for the
    homeowner to find their project again, nothing internal exposed."""

    id: str
    claim_token: str
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ProjectListItem(BaseModel):
    """Summary view for the contractor's project list — full detail
    (images, analysis, estimate) is deliberately left for a future
    GET /projects/{id} detail endpoint, not bloated into the list view."""

    id: str
    title: str
    status: str
    homeowner_name: str
    homeowner_email: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
    