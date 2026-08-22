"""Real Payment Verification Service preventing false positive revenue recovery."""
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logging import get_logger
from app.models import (
    RecoveryCase,
    RecoveryState,
    RecoveryAttempt,
    PaymentStatus,
    AuditLog,
    ActorType,
)
from app.providers.base import PaymentProvider, PaymentStatusResult
from app.providers.factory import get_payment_provider
from app.state_machine.machine import RecoveryStateMachine

logger = get_logger("recoverai.services.payment_verification")


class PaymentVerificationService:
    """
    Validates physical payment settlement against provider ledger before
    marking revenue as recovered or reconciling into financial metrics.
    """

    @classmethod
    async def verify_and_reconcile(
        cls,
        session: AsyncSession,
        case: RecoveryCase,
        provider_reference: str,
        attempted_amount: float,
        provider: Optional[PaymentProvider] = None,
        actor_id: str = "payment_verification_service",
    ) -> Tuple[bool, PaymentStatusResult]:
        """
        Query provider settlement status, verify funds were actually captured,
        record recovery attempt in DB, update case ledger, and write audit trail.
        """
        p = provider or get_payment_provider()
        
        logger.info(f"Verifying payment reference '{provider_reference}' for case '{case.id}'")
        verification: PaymentStatusResult = await p.verify_payment(provider_reference)

        from sqlalchemy import func
        stmt_cnt = select(func.count(RecoveryAttempt.id)).where(RecoveryAttempt.recovery_case_id == case.id)
        cnt_res = await session.execute(stmt_cnt)
        attempt_num = (cnt_res.scalar() or 0) + 1

        # Record recovery attempt record in database
        attempt = RecoveryAttempt(
            id=str(uuid.uuid4()),
            recovery_case_id=case.id,
            attempt_number=attempt_num,
            action_type=case.recommended_action or "RETRY_PAYMENT",
            result="SUCCESS" if verification.is_verified_captured else ("PENDING" if verification.status in ["pending", "authorized"] else "FAILED"),
            details_json={
                "provider_reference": provider_reference,
                "channel": case.recommended_channel or "SMART_RETRY",
                "status": verification.status,
                "is_sandbox": verification.is_sandbox,
                "raw_response": verification.raw_response,
            },
            attempted_at=verification.paid_at or datetime.now(timezone.utc),
        )
        session.add(attempt)

        if verification.is_verified_captured:
            logger.info(f"Payment '{provider_reference}' VERIFIED CAPTURED: ₹{attempted_amount:,.2f}")
            case.recovered_amount = attempted_amount

            # State transition to RECOVERED
            if case.status != RecoveryState.RECOVERED:
                audit = RecoveryStateMachine.transition(
                    case=case,
                    to_state=RecoveryState.RECOVERED,
                    actor_type=ActorType.RECOVERY_EXECUTOR,
                    actor_id=actor_id,
                    reason=f"Payment reference '{provider_reference}' verified captured in gateway ledger.",
                    metadata={
                        "provider_reference": provider_reference,
                        "verified_amount": attempted_amount,
                        "provider_status": verification.status,
                        "is_sandbox": verification.is_sandbox,
                    },
                )
                session.add(audit)
            await session.commit()
            return True, verification

        elif verification.status in ["pending", "authorized"]:
            logger.info(f"Payment '{provider_reference}' is PENDING/AWAITING_RESULT")
            if case.status != RecoveryState.AWAITING_RESULT:
                audit = RecoveryStateMachine.transition(
                    case=case,
                    to_state=RecoveryState.AWAITING_RESULT,
                    actor_type=ActorType.SYSTEM,
                    actor_id=actor_id,
                    reason=f"Payment reference '{provider_reference}' pending authorization in gateway.",
                    metadata={"provider_reference": provider_reference, "provider_status": verification.status},
                )
                session.add(audit)
            await session.commit()
            return False, verification

        else:
            logger.warning(f"Payment '{provider_reference}' VERIFICATION FAILED (status={verification.status})")
            # If attempts >= max retries, transition to FAILED / STOPPED, else RETRY_SCHEDULED
            max_retries = 3
            target_st = RecoveryState.FAILED if attempt_num >= max_retries else RecoveryState.RETRY_SCHEDULED
            if case.status != target_st and RecoveryStateMachine.can_transition(case.status, target_st):
                audit = RecoveryStateMachine.transition(
                    case=case,
                    to_state=target_st,
                    actor_type=ActorType.POLICY_ENGINE if attempt_num >= max_retries else ActorType.SYSTEM,
                    actor_id=actor_id,
                    reason=f"Payment attempt {attempt_num} declined ({verification.error_code or 'gateway_error'}).",
                    metadata={"provider_reference": provider_reference, "error_code": verification.error_code},
                )
                session.add(audit)
            await session.commit()
            return False, verification
