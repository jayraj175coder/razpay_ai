"""Audit Log model for immutable financial action tracking."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, Enum as SQLEnum, Text, JSON
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.enums import ActorType


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id = Column(String(64), ForeignKey("recovery_cases.id", ondelete="SET NULL"), nullable=True, index=True)
    actor_type = Column(SQLEnum(ActorType), nullable=False, index=True)
    actor_id = Column(String(128), nullable=True)
    action = Column(String(128), nullable=False, index=True)
    reason = Column(Text, nullable=True)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    # Relationships
    recovery_case = relationship("RecoveryCase", back_populates="audit_logs")
