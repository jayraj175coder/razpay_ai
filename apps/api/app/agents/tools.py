"""Agent Service Tools for Recovery Workflows."""
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Customer,
    Transaction,
    Payment,
    Subscription,
    Invoice,
    RecoveryCase,
    RecoveryPolicy,
    RecoveryAction,
    RecoveryActionType,
    PolicyDecision,
    ActionExecutionStatus,
    PromiseToPay,
    PromiseStatus,
    AuditLog,
    ActorType,
    RecoveryState,
)
from app.providers.factory import get_payment_provider
from app.risk.engine import RevenueRiskEngine, RiskAssessmentResult
from app.policies.engine import PolicyEngine, PolicyEvaluationResult


class AgentTools:
    """Service-layer tools available to the LangGraph Recovery Agent."""

    @classmethod
    async def get_customer_history(cls, session: AsyncSession, customer_id: str) -> Optional[Dict[str, Any]]:
        """Fetch customer profile, segment, and lifetime value."""
        stmt = select(Customer).where(Customer.id == customer_id)
        res = await session.execute(stmt)
        customer = res.scalars().first()
        if not customer:
            return None
        return {
            "id": customer.id,
            "name": customer.name,
            "email": customer.email,
            "segment": customer.segment.value,
            "lifetime_value": customer.lifetime_value,
        }

    @classmethod
    async def get_active_policy(cls, session: AsyncSession) -> RecoveryPolicy:
        """Fetch active recovery policy."""
        stmt = select(RecoveryPolicy).where(RecoveryPolicy.is_active == True).order_by(RecoveryPolicy.version.desc())
        res = await session.execute(stmt)
        policy = res.scalars().first()
        if not policy:
            policy = RecoveryPolicy(
                name="Default Dynamic Policy",
                version=1,
                is_active=True,
                max_payment_retries=3,
                max_messages=2,
                communication_window_hours=168,
                max_discount_pct=5.0,
                human_approval_threshold=100000.0,
            )
            session.add(policy)
            await session.flush()
        return policy

    @classmethod
    async def create_payment_link(
        cls,
        customer_id: str,
        amount: float,
        description: str,
        provider_name: str = "mock",
    ) -> Dict[str, Any]:
        """Generate a hosted payment link using payment provider."""
        provider = get_payment_provider(provider_name)
        result = await provider.create_payment_link(
            customer_id=customer_id,
            amount=amount,
            description=description,
        )
        return {
            "payment_link_id": result.payment_link_id,
            "short_url": result.short_url,
            "expires_at": result.expires_at.isoformat(),
            "is_sandbox": result.is_sandbox,
        }

    @classmethod
    async def execute_retry_payment(
        cls,
        transaction_id: str,
        amount: float,
        currency: str = "INR",
        provider_name: str = "mock",
    ) -> Dict[str, Any]:
        """Trigger payment retry via gateway."""
        provider = get_payment_provider(provider_name)
        result = await provider.retry_payment(
            transaction_id=transaction_id,
            amount=amount,
            currency=currency,
        )
        return {
            "success": result.success,
            "provider_reference": result.provider_reference,
            "failure_code": result.failure_code,
            "failure_message": result.failure_message,
            "is_sandbox": result.is_sandbox,
        }
