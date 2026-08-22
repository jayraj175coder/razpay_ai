"""Promise to Pay model."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Enum as SQLEnum, Text
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.enums import PromiseStatus


class PromiseToPay(Base):
    __tablename__ = "promises_to_pay"

    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    recovery_case_id = Column(String(64), ForeignKey("recovery_cases.id", ondelete="CASCADE"), nullable=False, index=True)
    customer_id = Column(String(64), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True)
    
    promised_amount = Column(Float, nullable=False)
    promise_date = Column(DateTime(timezone=True), nullable=False)
    confidence = Column(Float, default=0.9, nullable=False)
    raw_text = Column(Text, nullable=True)
    
    status = Column(SQLEnum(PromiseStatus), default=PromiseStatus.PROMISED, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    fulfilled_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    recovery_case = relationship("RecoveryCase", back_populates="promises")
    customer = relationship("Customer", back_populates="promises")
