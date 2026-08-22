"""Recovery Attempt model."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship

from app.core.database import Base


class RecoveryAttempt(Base):
    __tablename__ = "recovery_attempts"

    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    recovery_case_id = Column(String(64), ForeignKey("recovery_cases.id", ondelete="CASCADE"), nullable=False, index=True)
    attempt_number = Column(Integer, default=1, nullable=False)
    action_type = Column(String(64), nullable=False)
    result = Column(String(64), nullable=False)  # SUCCESS, FAILED, TIMEOUT, REJECTED
    details_json = Column(JSON, nullable=True)
    attempted_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    recovery_case = relationship("RecoveryCase", back_populates="attempts")
