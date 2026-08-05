
import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Column, String, Text, Integer, Float, ForeignKey, DateTime, Enum, Boolean
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.session import Base


def gen_uuid():
    return str(uuid.uuid4())


class UserRole(str, enum.Enum):
    contractor = "contractor"
    admin = "admin"


class ProjectStatus(str, enum.Enum):
    pending_analysis = "pending_analysis"
    awaiting_info = "awaiting_info"
    scoped = "scoped"
    estimated = "estimated"
    approved = "approved"
    archived = "archived"


class User(Base):
    """Contractor / admin accounts. Homeowners are NOT users — they access
    their project via a claim-link token, kept out of the auth system
    entirely to reduce attack surface."""
    __tablename__ = "users"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.contractor)
    is_active = Column(Boolean, default=True, nullable=False)
    failed_login_attempts = Column(Integer, default=0, nullable=False)
    locked_until = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

class Project(Base):
    __tablename__ = "projects"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    status = Column(Enum(ProjectStatus), nullable=False, default=ProjectStatus.pending_analysis)

    # Homeowner contact info (no account — captured directly on the project)
    homeowner_name = Column(String, nullable=False)
    homeowner_email = Column(String, nullable=False, index=True)
    homeowner_phone = Column(String, nullable=True)
    property_location = Column(String, nullable=True)
    desired_timeline = Column(String, nullable=True)
    budget_range = Column(String, nullable=True)

    # Single-purpose access token for the homeowner's status page.
    # High-entropy, indexed, expiring — never the primary key, never
    # sequential/guessable.
    claim_token = Column(String, unique=True, nullable=False, index=True)
    claim_token_expires_at = Column(DateTime, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    images = relationship("ProjectImage", back_populates="project", cascade="all, delete-orphan")
    analysis = relationship("ProjectAnalysis", back_populates="project", uselist=False, cascade="all, delete-orphan")
    estimate = relationship("EstimateResult", back_populates="project", uselist=False, cascade="all, delete-orphan")
    messages = relationship("Message", back_populates="project", cascade="all, delete-orphan")
