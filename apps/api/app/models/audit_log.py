"""Audit Log model for immutable cryptographic financial action tracking."""
import hashlib
import uuid
from datetime import datetime, timezone
from typing import Optional
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
    prev_hash = Column(String(64), nullable=True)
    entry_hash = Column(String(64), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    # Relationships
    recovery_case = relationship("RecoveryCase", back_populates="audit_logs")

    @classmethod
    def compute_hash(
        cls,
        entry_id: str,
        case_id: Optional[str],
        actor_type: str,
        action: str,
        reason: Optional[str],
        created_at: datetime,
        prev_hash: Optional[str] = None,
    ) -> str:
        """Compute cryptographic SHA-256 hash chaining for tamper evidence."""
        p_hash = prev_hash or "0" * 64
        c_str = created_at.isoformat() if isinstance(created_at, datetime) else str(created_at)
        raw = f"{p_hash}:{entry_id}:{case_id or ''}:{actor_type}:{action}:{reason or ''}:{c_str}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.id:
            self.id = str(uuid.uuid4())
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc)
        if not self.entry_hash:
            actor_type_val = self.actor_type.value if hasattr(self.actor_type, "value") else str(self.actor_type or "")
            self.entry_hash = self.compute_hash(
                entry_id=self.id,
                case_id=self.case_id,
                actor_type=actor_type_val,
                action=self.action or "",
                reason=self.reason,
                created_at=self.created_at,
                prev_hash=self.prev_hash,
            )
