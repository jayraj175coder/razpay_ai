"""Recovery Action model."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, Enum as SQLEnum, Text, JSON
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.enums import RecoveryActionType, PolicyDecision, ActionExecutionStatus


class RecoveryAction(Base):
    __tablename__ = "recovery_actions"

    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    recovery_case_id = Column(String(64), ForeignKey("recovery_cases.id", ondelete="CASCADE"), nullable=False, index=True)
    action_type = Column(SQLEnum(RecoveryActionType), nullable=False)
    action_reason = Column(Text, nullable=False)
    
    policy_decision = Column(SQLEnum(PolicyDecision), default=PolicyDecision.ALLOWED, nullable=False)
    policy_reason = Column(Text, nullable=True)
    
    status = Column(SQLEnum(ActionExecutionStatus), default=ActionExecutionStatus.PENDING, nullable=False)
    payload_json = Column(JSON, nullable=True)  # Parameters such as discount %, retry delay, email template
    result_json = Column(JSON, nullable=True)   # Provider response, message id, etc.
    
    executed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    recovery_case = relationship("RecoveryCase", back_populates="actions")
