"""Recovery Policy model."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, JSON

from app.core.database import Base


class RecoveryPolicy(Base):
    __tablename__ = "recovery_policies"

    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(128), default="Default Recovery Policy", nullable=False)
    version = Column(Integer, default=1, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    
    # Deterministic policy bounds
    max_payment_retries = Column(Integer, default=3, nullable=False)
    max_messages = Column(Integer, default=2, nullable=False)  # max communications per window
    communication_window_hours = Column(Integer, default=168, nullable=False)  # 7 days
    max_discount_pct = Column(Float, default=5.0, nullable=False)
    human_approval_threshold = Column(Float, default=100000.0, nullable=False)  # Transactions >= ₹1,00,000 require approval
    retry_delay_hours = Column(Integer, default=24, nullable=False)
    escalation_delay_hours = Column(Integer, default=72, nullable=False)
    
    # Mandate-specific deterministic bounds (NPCI cycles)
    mandate_retry_window_hours = Column(Integer, default=24, nullable=False)
    max_mandate_attempts_per_cycle = Column(Integer, default=3, nullable=False)
    
    rules_json = Column(JSON, nullable=True)  # Detailed custom rule overrides
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
