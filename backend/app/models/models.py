
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
    projects = relationship("Project", back_populates="contractor")
    password_hash = Column(String, nullable=False)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.contractor)
    is_active = Column(Boolean, default=True, nullable=False)
    failed_login_attempts = Column(Integer, default=0, nullable=False)
    locked_until = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

class Project(Base):
    __tablename__ = "projects"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    contractor_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False, index=True)
    contractor = relationship("User", back_populates="projects")
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

class ProjectImage(Base):
    __tablename__ = "project_images"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    project_id = Column(UUID(as_uuid=False), ForeignKey("projects.id"), nullable=False)
    # Stored path uses a randomized filename, never the user-supplied one,
    # to prevent path traversal / overwrite attacks.
    storage_path = Column(String, nullable=False)
    original_filename = Column(String, nullable=False)
    content_type = Column(String, nullable=False)
    size_bytes = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    project = relationship("Project", back_populates="images")


class ProjectAnalysis(Base):
    __tablename__ = "project_analyses"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    project_id = Column(UUID(as_uuid=False), ForeignKey("projects.id"), nullable=False, unique=True)
    category = Column(String, nullable=True)
    confidence = Column(Float, nullable=True)
    complexity = Column(String, nullable=True)
    missing_info = Column(Text, nullable=True)  # JSON-encoded list
    follow_up_questions = Column(Text, nullable=True)  # JSON-encoded list
    model_version = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    project = relationship("Project", back_populates="analysis")

class EstimateResult(Base):
    __tablename__ = "estimate_results"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    project_id = Column(UUID(as_uuid=False), ForeignKey("projects.id"), nullable=False, unique=True)
    scope_of_work = Column(Text, nullable=True)  # JSON-encoded list of line items
    estimate_min = Column(Float, nullable=True)
    estimate_max = Column(Float, nullable=True)
    confidence = Column(String, nullable=True)
    assumptions = Column(Text, nullable=True)  # JSON-encoded list
    risk_factors = Column(Text, nullable=True)  # JSON-encoded list
    approved_by_contractor = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    project = relationship("Project", back_populates="estimate")


class Message(Base):
    """Follow-up Q&A thread between system/contractor and homeowner."""
    __tablename__ = "messages"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    project_id = Column(UUID(as_uuid=False), ForeignKey("projects.id"), nullable=False)
    sender = Column(String, nullable=False)  # 'system' | 'contractor' | 'homeowner'
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    project = relationship("Project", back_populates="messages")

class AuditLog(Base):
    """Security-relevant event log: logins, failed logins, admin actions.
    No PII payloads or secrets are ever written here."""
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    actor_id = Column(UUID(as_uuid=False), nullable=True)  # user id if known
    actor_ip = Column(String, nullable=True)
    action = Column(String, nullable=False)  # e.g. "login_success", "login_failed", "project_status_change"
    resource_type = Column(String, nullable=True)
    resource_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
