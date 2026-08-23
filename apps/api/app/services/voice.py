"""Hinglish AI Voice Recovery and Conversational Telephony Service."""
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    RecoveryCase,
    Customer,
    RecoveryAction,
    RecoveryActionType,
    PolicyDecision,
    ActionExecutionStatus,
    AuditLog,
    ActorType,
    RecoveryState,
)
from app.agents.llm_client import llm_client
from app.agents.schemas import VoiceScriptOutput
from app.agents.tools import AgentTools
from app.services.promises import PromiseService


class VoiceRecoveryService:
    """Manages AI-driven Hinglish Voice Recovery scripts, interactive calls, and promise capture."""

    @classmethod
    async def generate_voice_script(
        cls,
        session: AsyncSession,
        case_id: str,
        language: str = "hinglish",
    ) -> Dict[str, Any]:
        """Generate tailored conversational Hinglish recovery audio script for a recovery case."""
        stmt = (
            select(RecoveryCase)
            .where(RecoveryCase.id == case_id)
            .options(selectinload(RecoveryCase.customer))
        )
        res = await session.execute(stmt)
        case = res.scalars().first()
        if not case:
            raise ValueError(f"Recovery case {case_id} not found")

        cust_name = case.customer.name if case.customer else "Valued Customer"
        cust_phone = case.customer.phone if case.customer else "+919876543210"

        context = {
            "failure_code": case.root_cause or "insufficient_funds",
            "amount": case.amount_at_risk,
            "customer_name": cust_name,
            "customer_phone": cust_phone,
            "source_type": case.source_type.value,
            "lifetime_value": case.customer.lifetime_value if case.customer else 0.0,
            "language": language,
        }

        prompt = (
            f"Generate a personalized {language} voice recovery script for {cust_name}. "
            f"Amount: INR {case.amount_at_risk:.2f}, Root Cause: '{case.root_cause}', "
            f"Source: {case.source_type.value}."
        )
        system_prompt = (
            "You are a professional, empathetic Indian fintech customer success AI. "
            "Generate natural spoken Hinglish copy (code-mixed Hindi + English) that is courteous, "
            "explains the transaction failure gently, and offers an instant 1-click Razorpay payment link."
        )

        script: VoiceScriptOutput = await llm_client.generate_structured(
            prompt=prompt,
            system_prompt=system_prompt,
            schema=VoiceScriptOutput,
            context=context,
        )

        return {
            "case_id": case.id,
            "customer_id": case.customer_id,
            "customer_name": cust_name,
            "customer_phone": cust_phone,
            "amount_at_risk": case.amount_at_risk,
            "language": language,
            "script_hinglish": script.script_text_hinglish,
            "script_english": script.script_text_english,
            "call_intent": script.call_intent,
            "voice_tone": script.voice_tone,
            "suggested_followup_action": script.suggested_followup_action.value,
            "dispatch_payment_link": script.dispatch_payment_link,
            "estimated_duration_seconds": script.estimated_duration_seconds,
        }

    @classmethod
    async def simulate_voice_call(
        cls,
        session: AsyncSession,
        case_id: str,
        customer_response_text: Optional[str] = None,
        operator_id: str = "ai_voice_agent",
    ) -> Dict[str, Any]:
        """
        Simulates an end-to-end interactive Hinglish voice recovery call:
        1. Speaks tailored Hinglish script
        2. Ingests customer voice response (if provided) and automatically extracts Promise-to-Pay
        3. Dispatches 1-click Razorpay recovery link via SMS/WhatsApp
        4. Writes an immutable audit trail
        """
        script_data = await cls.generate_voice_script(session=session, case_id=case_id)
        
        stmt = (
            select(RecoveryCase)
            .where(RecoveryCase.id == case_id)
            .options(selectinload(RecoveryCase.customer))
        )
        res = await session.execute(stmt)
        case = res.scalars().first()
        if not case:
            raise ValueError(f"Recovery case {case_id} not found")

        call_id = f"CALL-VOICE-{uuid.uuid4().hex[:8].upper()}"

        # 1. Create payment link for instant dispatch
        link_res = await AgentTools.create_payment_link(
            customer_id=case.customer_id,
            amount=case.amount_at_risk,
            description=f"RecoverAI Voice Recovery Link for {case.id}",
        )

        # 2. Extract promise if customer response is provided
        promise_result = None
        if customer_response_text:
            promise_result = await PromiseService.extract_and_record(
                session=session,
                case_id=case.id,
                customer_id=case.customer_id,
                message_text=customer_response_text,
            )

        # 3. Record RecoveryAction
        action_rec = RecoveryAction(
            id=str(uuid.uuid4()),
            recovery_case_id=case.id,
            action_type=RecoveryActionType.TRIGGER_HINGLISH_VOICE_CALL,
            action_reason=f"Interactive Hinglish voice recovery call completed (Call ID: {call_id})",
            policy_decision=PolicyDecision.ALLOWED,
            policy_reason="Compliant with communication frequency and voice recovery safety limits.",
            status=ActionExecutionStatus.EXECUTED,
            payload_json={
                "call_id": call_id,
                "script": script_data["script_hinglish"],
                "customer_response": customer_response_text,
                "payment_link": link_res["short_url"],
            },
            result_json={
                "call_status": "COMPLETED",
                "call_duration_seconds": script_data["estimated_duration_seconds"],
                "promise_captured": bool(promise_result and promise_result.get("has_promise")),
            },
            executed_at=datetime.now(timezone.utc),
        )
        session.add(action_rec)

        # 4. Audit Log
        audit = AuditLog(
            id=str(uuid.uuid4()),
            case_id=case.id,
            actor_type=ActorType.AI_AGENT,
            actor_id=operator_id,
            action="HINGLISH_VOICE_CALL_COMPLETED",
            reason=f"Outbound AI Hinglish voice recovery call connected with {script_data['customer_name']}.",
            metadata_json={
                "call_id": call_id,
                "script_hinglish": script_data["script_hinglish"],
                "customer_response": customer_response_text,
                "payment_link_id": link_res.get("payment_link_id"),
                "promise_result": promise_result,
            },
            created_at=datetime.now(timezone.utc),
        )
        session.add(audit)
        await session.commit()

        return {
            "success": True,
            "call_id": call_id,
            "case_id": case.id,
            "customer_name": script_data["customer_name"],
            "script_hinglish": script_data["script_hinglish"],
            "script_english": script_data["script_english"],
            "customer_response": customer_response_text,
            "promise": promise_result,
            "payment_link": link_res,
            "call_status": "COMPLETED",
            "call_duration_seconds": script_data["estimated_duration_seconds"],
        }
