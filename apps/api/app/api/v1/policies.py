"""Policy Configuration and Versioning API Router."""
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models import RecoveryPolicy, AuditLog, ActorType

router = APIRouter()


class PolicyCreateRequest(BaseModel):
    name: str = Field(default="Custom Recovery Policy")
    max_payment_retries: int = Field(default=3, ge=1, le=10)
    max_messages: int = Field(default=2, ge=1, le=10)
    communication_window_hours: int = Field(default=168, ge=24, le=720)
    max_discount_pct: float = Field(default=5.0, ge=0.0, le=50.0)
    human_approval_threshold: float = Field(default=100000.0, ge=1000.0)
    retry_delay_hours: int = Field(default=24, ge=1, le=168)
    escalation_delay_hours: int = Field(default=72, ge=1, le=336)
    mandate_retry_window_hours: int = Field(default=24, ge=1, le=168)
    max_mandate_attempts_per_cycle: int = Field(default=3, ge=1, le=10)
    rules_json: Optional[Dict[str, Any]] = None


@router.get("/active", status_code=status.HTTP_200_OK)
async def get_active_policy(db: AsyncSession = Depends(get_db)):
    """Fetch currently active recovery policy."""
    stmt = select(RecoveryPolicy).where(RecoveryPolicy.is_active == True).order_by(desc(RecoveryPolicy.version))
    res = await db.execute(stmt)
    policy = res.scalars().first()
    if not policy:
        raise HTTPException(status_code=404, detail="No active policy found")
    return {
        "id": policy.id,
        "name": policy.name,
        "version": policy.version,
        "is_active": policy.is_active,
        "max_payment_retries": policy.max_payment_retries,
        "max_messages": policy.max_messages,
        "communication_window_hours": policy.communication_window_hours,
        "max_discount_pct": policy.max_discount_pct,
        "human_approval_threshold": policy.human_approval_threshold,
        "retry_delay_hours": policy.retry_delay_hours,
        "escalation_delay_hours": policy.escalation_delay_hours,
        "mandate_retry_window_hours": policy.mandate_retry_window_hours,
        "max_mandate_attempts_per_cycle": policy.max_mandate_attempts_per_cycle,
        "rules": policy.rules_json or {},
        "created_at": policy.created_at.isoformat(),
    }


@router.get("", status_code=status.HTTP_200_OK)
async def list_policies(db: AsyncSession = Depends(get_db)):
    """List all versioned recovery policies."""
    stmt = select(RecoveryPolicy).order_by(desc(RecoveryPolicy.version))
    res = await db.execute(stmt)
    policies = res.scalars().all()
    return {
        "policies": [
            {
                "id": p.id,
                "name": p.name,
                "version": p.version,
                "is_active": p.is_active,
                "max_payment_retries": p.max_payment_retries,
                "max_messages": p.max_messages,
                "communication_window_hours": p.communication_window_hours,
                "max_discount_pct": p.max_discount_pct,
                "human_approval_threshold": p.human_approval_threshold,
                "retry_delay_hours": p.retry_delay_hours,
                "escalation_delay_hours": p.escalation_delay_hours,
                "mandate_retry_window_hours": p.mandate_retry_window_hours,
                "max_mandate_attempts_per_cycle": p.max_mandate_attempts_per_cycle,
                "rules": p.rules_json or {},
                "created_at": p.created_at.isoformat(),
            }
            for p in policies
        ],
        "count": len(policies),
    }


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_policy_version(
    req: PolicyCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Create a new versioned recovery policy and set it as active."""
    # Find latest version
    stmt = select(RecoveryPolicy).order_by(desc(RecoveryPolicy.version))
    res = await db.execute(stmt)
    latest = res.scalars().first()
    next_version = (latest.version + 1) if latest else 1

    # Deactivate previous active policies
    if latest:
        stmt_all = select(RecoveryPolicy).where(RecoveryPolicy.is_active == True)
        res_all = await db.execute(stmt_all)
        for p in res_all.scalars().all():
            p.is_active = False

    new_policy = RecoveryPolicy(
        id=str(uuid.uuid4()),
        name=req.name,
        version=next_version,
        is_active=True,
        max_payment_retries=req.max_payment_retries,
        max_messages=req.max_messages,
        communication_window_hours=req.communication_window_hours,
        max_discount_pct=req.max_discount_pct,
        human_approval_threshold=req.human_approval_threshold,
        retry_delay_hours=req.retry_delay_hours,
        escalation_delay_hours=req.escalation_delay_hours,
        mandate_retry_window_hours=req.mandate_retry_window_hours,
        max_mandate_attempts_per_cycle=req.max_mandate_attempts_per_cycle,
        rules_json=req.rules_json or {
            "disallowed_failure_codes": ["fraud_suspected", "stolen_card", "account_frozen", "sanction_block"],
        },
        created_at=datetime.now(timezone.utc),
    )
    db.add(new_policy)

    # Audit policy update
    audit = AuditLog(
        case_id=None,
        actor_type=ActorType.HUMAN_OPERATOR,
        actor_id="operator_policy_admin",
        action="POLICY_VERSION_CREATED",
        reason=f"Published Policy v{next_version} ({req.name}) with threshold ₹{req.human_approval_threshold:,.0f}",
        metadata_json=req.model_dump(),
    )
    db.add(audit)
    await db.commit()

    return {
        "success": True,
        "policy_id": new_policy.id,
        "version": new_policy.version,
        "name": new_policy.name,
    }
