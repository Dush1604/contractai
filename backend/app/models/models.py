
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
    