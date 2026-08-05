
"""Pydantic schemas for contractor registration and login."""
from pydantic import BaseModel, EmailStr, Field, ConfigDict


class ContractorRegister(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: str = Field(..., min_length=12, max_length=128)


class ContractorLogin(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: str = Field(..., min_length=1, max_length=128)


class ContractorResponse(BaseModel):
    id: str
    email: str
    role: str

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    