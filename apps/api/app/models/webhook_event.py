"""Webhook Event model with strict idempotency constraint."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Enum as SQLEnum, Text, JSON, UniqueConstraint

from app.core.database import Base
from app.models.enums import WebhookStatus


class WebhookEvent(Base):
    __tablename__ = "webhook_events"

    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    provider = Column(String(64), default="razorpay", nullable=False, index=True)
    event_id = Column(String(128), nullable=False, index=True)
    event_type = Column(String(128), nullable=False, index=True)
    payload_hash = Column(String(64), nullable=False, index=True)  # SHA-256 hash of payload
    payload = Column(JSON, nullable=False)
    
    received_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    processed_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(SQLEnum(WebhookStatus), default=WebhookStatus.RECEIVED, nullable=False, index=True)
    error_message = Column(Text, nullable=True)

    # Unique constraint enforcing idempotency across provider, event_id, and payload_hash
    __table_args__ = (
        UniqueConstraint("provider", "event_id", "payload_hash", name="uq_webhook_event_idempotency"),
    )
