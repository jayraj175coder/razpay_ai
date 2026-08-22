"""Recovery Case model."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Enum as SQLEnum, Text, JSON
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.enums import RecoverySourceType, RecoveryState, RiskCategory


class RecoveryCase(Base):
    __tablename__ = "recovery_cases"

    id = Column(String(64), primary_key=True, default=lambda: f"RCV-{uuid.uuid4().hex[:8].upper()}")
    source_type = Column(SQLEnum(RecoverySourceType), nullable=False, index=True)
    source_id = Column(String(128), nullable=False, index=True)
    customer_id = Column(String(64), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True)
    
    amount_at_risk = Column(Float, nullable=False)
    currency = Column(String(8), default="INR", nullable=False)
    recovery_probability = Column(Float, default=0.5, nullable=False)
    priority_score = Column(Float, default=50.0, nullable=False)
    risk_category = Column(SQLEnum(RiskCategory), default=RiskCategory.MEDIUM, nullable=False)
    
    root_cause = Column(String(255), nullable=True)
    root_cause_explanation = Column(Text, nullable=True)
    recommended_action = Column(String(255), nullable=True)
    recommended_channel = Column(String(64), nullable=True)  # EMAIL, WHATSAPP, PAYMENT_LINK, RETRY
    ai_reasoning = Column(Text, nullable=True)
    signals_json = Column(JSON, nullable=True)  # Explainable signals breakdown
    
    status = Column(SQLEnum(RecoveryState), default=RecoveryState.DETECTED, nullable=False, index=True)
    stopping_reason = Column(String(255), nullable=True)
    recovered_amount = Column(Float, default=0.0, nullable=False)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    customer = relationship("Customer", back_populates="recovery_cases")
    actions = relationship("RecoveryAction", back_populates="recovery_case", cascade="all, delete-orphan")
    attempts = relationship("RecoveryAttempt", back_populates="recovery_case", cascade="all, delete-orphan")
    promises = relationship("PromiseToPay", back_populates="recovery_case", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="recovery_case", cascade="all, delete-orphan")
