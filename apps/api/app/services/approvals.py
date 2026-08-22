"""Human-in-the-loop Approval and Escalation Service."""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    RecoveryCase,
    RecoveryState,
    RecoveryAction,
    RecoveryActionType,
    PolicyDecision,
    ActionExecutionStatus,
    AuditLog,
    ActorType,
    Customer,
)
from app.state_machine.machine import RecoveryStateMachine
from app.providers.factory import get_payment_provider


class ApprovalService:
    """Manages human operator decisioning on escalated recovery actions."""

    @classmethod
    async def list_pending_approvals(cls, session: AsyncSession) -> List[Dict[str, Any]]:
        """List all cases currently waiting for human approval."""
        stmt = (
            select(RecoveryCase)
            .where(RecoveryCase.status.in_([RecoveryState.ESCALATED, RecoveryState.POLICY_CHECK]))
            .options(
                selectinload(RecoveryCase.customer),
                selectinload(RecoveryCase.actions),
            )
            .order_by(desc(RecoveryCase.amount_at_risk))
        )
        res = await session.execute(stmt)
        cases = res.scalars().all()

        results = []
        for c in cases:
            latest_action = c.actions[0] if c.actions else None
            results.append({
                "case_id": c.id,
                "customer_id": c.customer_id,
                "customer_name": c.customer.name if c.customer else "Unknown",
                "customer_email": c.customer.email if c.customer else "",
                "customer_segment": c.customer.segment.value if c.customer else "RETAIL",
                "customer_ltv": c.customer.lifetime_value if c.customer else 0.0,
                "amount_at_risk": c.amount_at_risk,
                "currency": c.currency,
                "source_type": c.source_type.value,
                "recommended_action": c.recommended_action or "RETRY_PAYMENT",
                "recommended_channel": c.recommended_channel or "SMART_RETRY",
                "ai_reasoning": c.ai_reasoning,
                "policy_reason": latest_action.policy_reason if latest_action else "Exceeds automated threshold",
                "status": c.status.value,
                "created_at": c.created_at.isoformat(),
            })
        return results

    @classmethod
    async def process_decision(
        cls,
        session: AsyncSession,
        case_id: str,
        decision: str,  # "APPROVE", "REJECT", "MODIFY"
        operator_id: str = "operator_admin",
        reason: Optional[str] = None,
        modified_amount: Optional[float] = None,
        modified_action: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Record human operator approval/rejection decision and trigger execution."""
        stmt = (
            select(RecoveryCase)
            .where(RecoveryCase.id == case_id)
            .options(selectinload(RecoveryCase.actions))
        )
        res = await session.execute(stmt)
        case = res.scalars().first()
        if not case:
            raise ValueError(f"Case {case_id} not found")

        decision_upper = decision.upper()

        if decision_upper == "REJECT":
            audit = RecoveryStateMachine.transition(
                case=case,
                to_state=RecoveryState.STOPPED,
                actor_type=ActorType.HUMAN_OPERATOR,
                actor_id=operator_id,
                reason=reason or "Rejected by risk operator",
                metadata={"decision": "REJECT"},
            )
            session.add(audit)
            await session.commit()
            return {"success": True, "case_id": case.id, "status": case.status.value, "decision": "REJECTED"}

        elif decision_upper in ["APPROVE", "MODIFY"]:
            # Transition to APPROVED
            audit_app = RecoveryStateMachine.transition(
                case=case,
                to_state=RecoveryState.APPROVED,
                actor_type=ActorType.HUMAN_OPERATOR,
                actor_id=operator_id,
                reason=reason or "Approved by operator",
                metadata={
                    "decision": decision_upper,
                    "original_action": case.recommended_action,
                    "modified_amount": modified_amount,
                    "modified_action": modified_action,
                },
            )
            session.add(audit_app)

            exec_amount = modified_amount if modified_amount is not None else case.amount_at_risk
            
            # Execute through gateway
            provider = get_payment_provider()
            retry_res = await provider.retry_payment(
                transaction_id=case.source_id,
                amount=exec_amount,
                currency=case.currency,
                force_outcome="SUCCESS",
            )

            if retry_res.success:
                case.recovered_amount = exec_amount
                audit_rec = RecoveryStateMachine.transition(
                    case=case,
                    to_state=RecoveryState.RECOVERED,
                    actor_type=ActorType.RECOVERY_EXECUTOR,
                    actor_id=f"operator_approved_{operator_id}",
                    reason=f"Payment of ₹{exec_amount:,.0f} recovered via human approval.",
                    metadata={"provider_reference": retry_res.provider_reference},
                )
                session.add(audit_rec)

            await session.commit()
            return {
                "success": True,
                "case_id": case.id,
                "status": case.status.value,
                "recovered_amount": case.recovered_amount,
                "decision": decision_upper,
            }

        raise ValueError(f"Invalid decision: {decision}")
