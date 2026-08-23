"""Provider-Agnostic LLM Client for RecoverAI Agent."""
import json
import re
from typing import Any, Dict, Optional, Type, TypeVar
from pydantic import BaseModel

from app.core.config import settings
from app.core.logging import get_logger
from app.agents.schemas import DiagnosisOutput, StrategyOutput, PromiseExtractionOutput, VoiceScriptOutput
from app.models.enums import RecoveryActionType, RiskCategory

logger = get_logger("recoverai.agents.llm")

T = TypeVar("T", bound=BaseModel)


class LLMClient:
    """
    Provider-agnostic LLM interface supporting Gemini, OpenAI, Anthropic,
    and a deterministic high-fidelity mock fallback.
    """

    def __init__(self, provider: Optional[str] = None):
        self.provider = (provider or settings.LLM_PROVIDER).lower().strip()

    async def generate_structured(
        self,
        prompt: str,
        system_prompt: str,
        schema: Type[T],
        context: Optional[Dict[str, Any]] = None,
    ) -> T:
        """Generate structured response matching the Pydantic schema."""
        if self.provider == "gemini" and settings.GEMINI_API_KEY:
            try:
                return await self._call_gemini(prompt, system_prompt, schema)
            except Exception as exc:
                logger.warning(f"Gemini API call failed, falling back to deterministic mock: {exc}")
                return self._call_mock(prompt, schema, context or {})

        elif self.provider == "openai" and settings.OPENAI_API_KEY:
            try:
                return await self._call_openai(prompt, system_prompt, schema)
            except Exception as exc:
                logger.warning(f"OpenAI API call failed, falling back to deterministic mock: {exc}")
                return self._call_mock(prompt, schema, context or {})

        # Default: Deterministic high-precision fallback
        return self._call_mock(prompt, schema, context or {})

    async def _call_gemini(self, prompt: str, system_prompt: str, schema: Type[T]) -> T:
        from google import genai
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        response = client.models.generate_content(
            model=settings.LLM_MODEL or "gemini-2.0-flash",
            contents=prompt,
            config={
                "system_instruction": system_prompt,
                "response_mime_type": "application/json",
                "response_schema": schema,
            },
        )
        return schema.model_validate_json(response.text)

    async def _call_openai(self, prompt: str, system_prompt: str, schema: Type[T]) -> T:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        completion = await client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            response_format=schema,
        )
        return completion.choices[0].message.parsed

    def _call_mock(self, prompt: str, schema: Type[T], context: Dict[str, Any]) -> T:
        """Deterministic context-aware mock generator for testing and offline development."""
        failure_code = str(context.get("failure_code", "")).lower()
        amount = float(context.get("amount", 0.0))
        customer_name = str(context.get("customer_name", "Valued Customer"))
        source_type = str(context.get("source_type", "PAYMENT_FAILURE"))
        ltv = float(context.get("lifetime_value", 0.0))

        if schema == DiagnosisOutput:
            if "npci" in failure_code or "bank_server" in failure_code:
                return DiagnosisOutput(
                    root_cause=failure_code if failure_code in ["npci_downtime", "bank_server_error"] else "npci_downtime",
                    explanation=f"Infrastructure outage at NPCI / issuing bank switch for {customer_name}. Transient network error.",
                    confidence=0.95,
                    risk_category=RiskCategory.LOW if amount < 25000 else RiskCategory.MEDIUM,
                )
            elif "mandate_revoked" in failure_code:
                return DiagnosisOutput(
                    root_cause="mandate_revoked",
                    explanation=f"Customer {customer_name} revoked the recurring mandate at issuing bank. Automated retries prohibited; renewal required.",
                    confidence=0.97,
                    risk_category=RiskCategory.CRITICAL,
                )
            elif "mandate_expired" in failure_code:
                return DiagnosisOutput(
                    root_cause="mandate_expired",
                    explanation=f"Mandate validity period expired for {customer_name}. Requires fresh e-mandate authorization.",
                    confidence=0.94,
                    risk_category=RiskCategory.HIGH,
                )
            elif "low_balance_recurring" in failure_code:
                return DiagnosisOutput(
                    root_cause="low_balance_recurring",
                    explanation=f"Recurring mandate scheduled execution failed due to temporary low balance. Eligible for post-payroll resequencing.",
                    confidence=0.90,
                    risk_category=RiskCategory.MEDIUM,
                )
            elif "mandate_amount_exceeded" in failure_code:
                return DiagnosisOutput(
                    root_cause="mandate_amount_exceeded",
                    explanation=f"Debit amount ₹{amount:,.0f} exceeds max authorized mandate cap for {customer_name}.",
                    confidence=0.92,
                    risk_category=RiskCategory.MEDIUM,
                )
            elif "timeout" in failure_code or "network" in failure_code:
                return DiagnosisOutput(
                    root_cause="transient_gateway_timeout",
                    explanation=f"Transaction failed due to interbank network timeout. Customer {customer_name} has strong historical liquidity.",
                    confidence=0.94,
                    risk_category=RiskCategory.MEDIUM if amount < 100000 else RiskCategory.CRITICAL,
                )
            elif "expired" in failure_code:
                return DiagnosisOutput(
                    root_cause="card_expired",
                    explanation=f"Card expired on customer account. Automated payment attempts will fail until new card details or alternate payment method is provided.",
                    confidence=0.92,
                    risk_category=RiskCategory.HIGH,
                )
            elif "insufficient" in failure_code:
                return DiagnosisOutput(
                    root_cause="temporary_insufficient_funds",
                    explanation=f"Account balance sweep or temporary card limit reached for {customer_name} (LTV ₹{ltv:,.0f}).",
                    confidence=0.88,
                    risk_category=RiskCategory.CRITICAL if amount >= 100000 else RiskCategory.HIGH,
                )
            elif "checkout" in failure_code or "abandoned" in source_type.lower():
                return DiagnosisOutput(
                    root_cause="checkout_dropoff_otp",
                    explanation=f"Customer abandoned during 3DS OTP verification stage.",
                    confidence=0.89,
                    risk_category=RiskCategory.LOW if amount < 10000 else RiskCategory.MEDIUM,
                )
            elif "fraud" in failure_code or "stolen" in failure_code:
                return DiagnosisOutput(
                    root_cause="fraud_suspected",
                    explanation="High risk security signal detected on payment transaction. Automated recovery blocked.",
                    confidence=0.97,
                    risk_category=RiskCategory.CRITICAL,
                )
            else:
                return DiagnosisOutput(
                    root_cause="unclassified_payment_failure",
                    explanation=f"Payment declined with reason: '{failure_code}'. Manual investigation advised.",
                    confidence=0.75,
                    risk_category=RiskCategory.MEDIUM,
                )

        elif schema == StrategyOutput:
            if amount >= 100000.0:
                return StrategyOutput(
                    recommended_action=RecoveryActionType.SCHEDULE_CALL,
                    recommended_channel="PHONE_ESCALATION",
                    reasoning=f"Transaction amount ₹{amount:,.0f} exceeds ₹1,00,000 safety threshold. Dedicated account manager outreach recommended to protect customer relationship.",
                    customer_message=f"Hi {customer_name}, we noticed an issue settling your recent invoice of ₹{amount:,.0f}. Our account specialist will contact your team to assist with payment routing.",
                    retry_delay_hours=24,
                )
            elif failure_code in ["mandate_revoked", "mandate_expired"]:
                return StrategyOutput(
                    recommended_action=RecoveryActionType.REQUEST_MANDATE_RENEWAL,
                    recommended_channel="WHATSAPP",
                    reasoning=f"Mandate status is '{failure_code}'. Automated retry is prohibited; customer must re-authorize or renew e-mandate.",
                    customer_message=f"Hello {customer_name}, your recurring payment mandate requires re-authorization. Please click below to renew your mandate securely.",
                    retry_delay_hours=24,
                )
            elif failure_code in ["npci_downtime", "bank_server_error", "low_balance_recurring", "mandate_amount_exceeded"] or source_type == "MANDATE_FAILURE":
                return StrategyOutput(
                    recommended_action=RecoveryActionType.RESEQUENCE_MANDATE_RETRY,
                    recommended_channel="SMART_RETRY",
                    reasoning="Mandate failure eligible for NPCI cycle resequencing after cooling window.",
                    customer_message=None,
                    retry_delay_hours=24,
                )
            elif "timeout" in failure_code or "network" in failure_code:
                return StrategyOutput(
                    recommended_action=RecoveryActionType.RETRY_PAYMENT,
                    recommended_channel="SMART_RETRY",
                    reasoning="Transient infrastructure error. Optimal action is scheduled retry during low bank traffic window.",
                    customer_message=None,
                    retry_delay_hours=6,
                )
            elif "expired" in failure_code:
                return StrategyOutput(
                    recommended_action=RecoveryActionType.CREATE_PAYMENT_LINK,
                    recommended_channel="WHATSAPP",
                    reasoning="Card is expired. Delivering a 1-click Razorpay payment link via WhatsApp allows fast payment via UPI or alternate card.",
                    customer_message=f"Hello {customer_name}, your previous card is expired. Please click below to update payment details or pay ₹{amount:,.0f} instantly via UPI/Netbanking.",
                    retry_delay_hours=24,
                )
            elif "abandoned" in failure_code or "checkout" in source_type.lower():
                return StrategyOutput(
                    recommended_action=RecoveryActionType.SEND_PAYMENT_REMINDER,
                    recommended_channel="EMAIL",
                    reasoning="Cart dropoff recovery. Send instant reminder with 1-click checkout recovery link.",
                    customer_message=f"Hi {customer_name}, you left items in your cart worth ₹{amount:,.0f}. Click here to complete your order in 1 click.",
                    proposed_discount_pct=0.0,
                    retry_delay_hours=2,
                )
            else:
                return StrategyOutput(
                    recommended_action=RecoveryActionType.SEND_PAYMENT_REMINDER,
                    recommended_channel="EMAIL",
                    reasoning="Standard payment failure reminder with payment link.",
                    customer_message=f"Dear {customer_name}, your payment of ₹{amount:,.0f} was unsuccessful. Please use the link below to complete the transaction.",
                    retry_delay_hours=24,
                )

        elif schema == PromiseExtractionOutput:
            # Simple rule-based promise extractor
            prompt_text = prompt.lower()
            amount_match = re.search(r"(?:rs\.?|inr|₹)?\s*(\d+[\d,]*\d*)", prompt_text)
            extracted_amt = float(amount_match.group(1).replace(",", "")) if amount_match else None
            
            has_promise = any(w in prompt_text for w in ["will pay", "promise", "monday", "tomorrow", "wednesday", "friday", "by ", "clear kar dunga", "pay kar dunga", "dunga"])
            return PromiseExtractionOutput(
                has_promise=has_promise,
                promised_amount=extracted_amt,
                promised_date="2026-08-25",
                confidence=0.95 if has_promise else 0.1,
                notes="Extracted promise commitment from customer correspondence.",
            )
        elif schema == VoiceScriptOutput:
            intent = str(context.get("intent", "")).upper()
            if not intent:
                if "mandate" in failure_code:
                    intent = "MANDATE_RENEWAL"
                elif "checkout" in failure_code or "abandoned" in source_type.lower():
                    intent = "CHECKOUT_RESTORATION"
                elif amount >= 100000.0:
                    intent = "INVOICE_CLEARANCE"
                else:
                    intent = "PAYMENT_REMINDER"

            if "mandate" in failure_code:
                hinglish = f"Namaste {customer_name}! Hum RecoverAI payment desk se bol rahe hain. Aapka ₹{amount:,.0f} ka recurring mandate authorization expire ho gaya hai. Aapke WhatsApp pe humne 1-click renewal link share kiya hai, jisse aap 30 seconds mein mandate re-activate kar sakte hain. Thank you!"
                english = f"Hello {customer_name}, calling from RecoverAI payment services. Your recurring mandate of INR {amount:,.0f} requires re-authorization. We have sent a 1-click renewal link to your registered WhatsApp. Thank you."
            elif "checkout" in failure_code or "abandoned" in source_type.lower():
                hinglish = f"Namaste {customer_name}! Aapne ₹{amount:,.0f} ke cart items checkout stage pe chhod diye the. Kya aap order complete karna chahte hain? Humne WhatsApp pe instant 1-click checkout payment link bhej diya hai."
                english = f"Hello {customer_name}, we noticed incomplete checkout items worth INR {amount:,.0f}. A direct payment link has been delivered to your WhatsApp for instant completion."
            elif amount >= 100000.0:
                hinglish = f"Namaste {customer_name} ji! Main accounts support team se connect kar raha hoon. Aapke ₹{amount:,.0f} ke pending enterprise invoice ke settlement ke regarding baat karni thi. Kya hamara relationship manager aapko call par guide kar sakta hai?"
                english = f"Good day {customer_name}, calling from Enterprise Accounts regarding the pending invoice of INR {amount:,.0f}. Our account specialist is available to facilitate settlement."
            else:
                hinglish = f"Namaste {customer_name}! Aapka ₹{amount:,.0f} ka recent payment temporary bank network issue ki wajah se decline ho gaya tha. Humne aapke registered WhatsApp pe Razorpay 1-click payment link bheja hai jisse aap turant UPI ya card se pay kar sakte hain."
                english = f"Hello {customer_name}, your recent payment of INR {amount:,.0f} was unsuccessful due to a transient bank network issue. A secure 1-click payment link has been shared via WhatsApp."

            return VoiceScriptOutput(
                script_text_hinglish=hinglish,
                script_text_english=english,
                call_intent=intent,
                voice_tone="ENTERPRISE_EXECUTIVE" if amount >= 100000 else "POLITE_PROFESSIONAL",
                suggested_followup_action=RecoveryActionType.REQUEST_MANDATE_RENEWAL if "mandate" in failure_code else RecoveryActionType.CREATE_PAYMENT_LINK,
                dispatch_payment_link=True,
                estimated_duration_seconds=30,
            )

        raise ValueError(f"Unsupported schema: {schema}")


llm_client = LLMClient()
