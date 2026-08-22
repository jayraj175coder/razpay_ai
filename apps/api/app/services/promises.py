"""Promise-to-Pay Lifecycle and Extraction Service."""
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import PromiseToPay, PromiseStatus, Customer, RecoveryCase, RecoveryState, AuditLog, ActorType
from app.agents.llm_client import llm_client
from app.agents.schemas import PromiseExtractionOutput
from app.state_machine.machine import RecoveryStateMachine


class PromiseService:
    """Manages promise-to-pay extraction, tracking, and fulfillment lifecycle."""

    @classmethod
    async def extract_and_record(
        cls,
        session: AsyncSession,
        case_id: str,
        customer_id: str,
        message_text: str,
    ) -> Dict[str, Any]:
        """Extract structured promise commitments from natural language message and persist."""
        prompt = f"Extract payment promise from customer message: '{message_text}'"
        system_prompt = "You are a fintech collections specialist. Extract numerical amount and date promised."
        
        extracted: PromiseExtractionOutput = await llm_client.generate_structured(
            prompt=prompt,
            system_prompt=system_prompt,
            schema=PromiseExtractionOutput,
        )

        if not extracted.has_promise or not extracted.promised_amount:
            return {"has_promise": False, "message": "No explicit payment commitment detected."}

        # Parse date or default to 3 days ahead
        try:
            p_date = datetime.fromisoformat(extracted.promised_date or "")
            if p_date.tzinfo is None:
                p_date = p_date.replace(tzinfo=timezone.utc)
        except Exception:
            p_date = datetime.now(timezone.utc) + timedelta(days=3)

        promise = PromiseToPay(
            id=str(uuid.uuid4()),
            recovery_case_id=case_id,
            customer_id=customer_id,
            promised_amount=extracted.promised_amount,
            promise_date=p_date,
            confidence=extracted.confidence,
            raw_text=message_text,
            status=PromiseStatus.WAITING,
        )
        session.add(promise)

        # Log audit trail
        audit = AuditLog(
            case_id=case_id,
            actor_type=ActorType.AI_AGENT,
            actor_id="promise_extractor_v1",
            action="PROMISE_TO_PAY_RECORDED",
            reason=f"Customer committed to pay ₹{extracted.promised_amount:,.0f} by {p_date.strftime('%Y-%m-%d')}",
            metadata_json=extracted.model_dump(),
        )
        session.add(audit)
        await session.commit()

        return {
            "has_promise": True,
            "promise_id": promise.id,
            "promised_amount": promise.promised_amount,
            "promise_date": promise.promise_date.isoformat(),
            "confidence": promise.confidence,
            "status": promise.status.value,
        }

    @classmethod
    async def list_promises(
        cls,
        session: AsyncSession,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List all promises with customer and case metadata."""
        query = select(PromiseToPay).options(
            selectinload(PromiseToPay.customer),
            selectinload(PromiseToPay.recovery_case),
        ).order_by(desc(PromiseToPay.created_at))

        if status:
            query = query.where(PromiseToPay.status == PromiseStatus(status))

        res = await session.execute(query)
        promises = res.scalars().all()

        now = datetime.now(timezone.utc)
        results = []
        for p in promises:
            p_date = p.promise_date
            if p_date.tzinfo is None:
                p_date = p_date.replace(tzinfo=timezone.utc)
            days_remaining = (p_date - now).days
            results.append({
                "id": p.id,
                "case_id": p.recovery_case_id,
                "customer_id": p.customer_id,
                "customer_name": p.customer.name if p.customer else "Unknown",
                "customer_email": p.customer.email if p.customer else "",
                "promised_amount": p.promised_amount,
                "promise_date": p.promise_date.isoformat(),
                "days_remaining": days_remaining,
                "confidence": p.confidence,
                "raw_text": p.raw_text,
                "status": p.status.value,
                "created_at": p.created_at.isoformat(),
                "fulfilled_at": p.fulfilled_at.isoformat() if p.fulfilled_at else None,
            })
        return results

    @classmethod
    async def fulfill_promise(cls, session: AsyncSession, promise_id: str) -> Dict[str, Any]:
        """Mark promise as fulfilled upon payment confirmation."""
        stmt = select(PromiseToPay).where(PromiseToPay.id == promise_id).options(selectinload(PromiseToPay.recovery_case))
        res = await session.execute(stmt)
        p = res.scalars().first()
        if not p:
            raise ValueError("Promise not found")

        p.status = PromiseStatus.FULFILLED
        p.fulfilled_at = datetime.now(timezone.utc)

        # Update case
        if p.recovery_case:
            p.recovery_case.recovered_amount = p.promised_amount
            p.recovery_case.status = RecoveryState.RECOVERED

        audit = AuditLog(
            case_id=p.recovery_case_id,
            actor_type=ActorType.RECOVERY_EXECUTOR,
            actor_id="promise_tracker",
            action="PROMISE_FULFILLED",
            reason=f"Customer promise of ₹{p.promised_amount:,.0f} confirmed fulfilled.",
        )
        session.add(audit)
        await session.commit()
        return {"success": True, "promise_id": p.id, "status": p.status.value}

    @classmethod
    async def escalate_broken_promise(cls, session: AsyncSession, promise_id: str) -> Dict[str, Any]:
        """Mark promise as broken/escalated when past due."""
        stmt = select(PromiseToPay).where(PromiseToPay.id == promise_id).options(selectinload(PromiseToPay.recovery_case))
        res = await session.execute(stmt)
        p = res.scalars().first()
        if not p:
            raise ValueError("Promise not found")

        p.status = PromiseStatus.BROKEN

        if p.recovery_case:
            p.recovery_case.status = RecoveryState.ESCALATED

        audit = AuditLog(
            case_id=p.recovery_case_id,
            actor_type=ActorType.SYSTEM,
            actor_id="promise_tracker",
            action="PROMISE_BROKEN_ESCALATED",
            reason=f"Promise date elapsed without payment. Escalated to human operator.",
        )
        session.add(audit)
        await session.commit()
        return {"success": True, "promise_id": p.id, "status": p.status.value}
