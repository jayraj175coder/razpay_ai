"""Idempotent Webhook Event Processor for Razorpay and simulated events."""
import hashlib
import json
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models import (
    Customer,
    CustomerSegment,
    Transaction,
    TransactionStatus,
    TransactionType,
    Payment,
    PaymentStatus,
    Subscription,
    SubscriptionStatus,
    BillingCycle,
    Invoice,
    InvoiceStatus,
    RecoveryCase,
    RecoverySourceType,
    RecoveryState,
    WebhookEvent,
    WebhookStatus,
    AuditLog,
    ActorType,
)
from app.risk.engine import RevenueRiskEngine
from app.state_machine.machine import RecoveryStateMachine

logger = get_logger("recoverai.webhooks")


class WebhookProcessor:
    """Processes incoming payment and subscription webhook events with strict idempotency."""

    @classmethod
    def compute_payload_hash(cls, raw_payload: bytes) -> str:
        """Compute SHA-256 hash of the raw payload."""
        return hashlib.sha256(raw_payload).hexdigest()

    @classmethod
    async def process_event(
        cls,
        session: AsyncSession,
        provider: str,
        event_id: str,
        event_type: str,
        raw_payload: bytes,
        payload_dict: Dict[str, Any],
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Processes an incoming webhook event.
        
        Returns:
            (is_duplicate: bool, message: str, result_data: Optional[dict])
        """
        payload_hash = cls.compute_payload_hash(raw_payload)

        # 1. Check Idempotency
        stmt = select(WebhookEvent).where(
            WebhookEvent.provider == provider,
            WebhookEvent.event_id == event_id,
            WebhookEvent.payload_hash == payload_hash,
        )
        res = await session.execute(stmt)
        existing_event = res.scalars().first()

        if existing_event:
            logger.info(f"Duplicate webhook event detected: provider={provider} event_id={event_id} status={existing_event.status.value}")
            return True, "Duplicate event ignored (idempotent)", {"event_id": event_id, "status": "duplicate"}

        # 2. Persist Webhook Event in RECEIVED state
        webhook_record = WebhookEvent(
            id=str(uuid.uuid4()),
            provider=provider,
            event_id=event_id,
            event_type=event_type,
            payload_hash=payload_hash,
            payload=payload_dict,
            status=WebhookStatus.PROCESSING,
        )
        session.add(webhook_record)
        await session.flush()

        try:
            result_data = await cls._dispatch_event(session, event_type, payload_dict)
            webhook_record.status = WebhookStatus.PROCESSED
            webhook_record.processed_at = datetime.now(timezone.utc)
            await session.commit()
            return False, "Event processed successfully", result_data
        except Exception as exc:
            logger.error(f"Error processing webhook {event_id} ({event_type}): {exc}", exc_info=True)
            webhook_record.status = WebhookStatus.FAILED
            webhook_record.error_message = str(exc)
            await session.commit()
            raise

    @classmethod
    async def _dispatch_event(
        cls,
        session: AsyncSession,
        event_type: str,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Route event to respective handler."""
        if event_type == "payment.failed":
            return await cls._handle_payment_failed(session, payload)
        elif event_type == "payment.captured":
            return await cls._handle_payment_captured(session, payload)
        elif event_type == "subscription.payment_failed":
            return await cls._handle_subscription_failed(session, payload)
        elif event_type == "subscription.charged":
            return await cls._handle_subscription_charged(session, payload)
        elif event_type == "invoice.overdue":
            return await cls._handle_invoice_overdue(session, payload)
        elif event_type == "checkout.abandoned":
            return await cls._handle_checkout_abandoned(session, payload)
        else:
            logger.warning(f"Unhandled webhook event type: {event_type}")
            return {"status": "ignored", "event_type": event_type}

    @classmethod
    async def _ensure_customer(
        cls,
        session: AsyncSession,
        cust_data: Dict[str, Any],
    ) -> Customer:
        """Fetch or create customer from webhook data."""
        email = cust_data.get("email", "unknown@customer.com")
        stmt = select(Customer).where(Customer.email == email)
        res = await session.execute(stmt)
        customer = res.scalars().first()

        if not customer:
            customer = Customer(
                id=cust_data.get("id", f"cust_{uuid.uuid4().hex[:8]}"),
                name=cust_data.get("name", "New Customer"),
                email=email,
                phone=cust_data.get("phone", "+919800000000"),
                segment=CustomerSegment[cust_data.get("segment", "RETAIL")],
                lifetime_value=float(cust_data.get("lifetime_value", 0.0)),
            )
            session.add(customer)
            await session.flush()
        return customer

    @classmethod
    async def _handle_payment_failed(
        cls,
        session: AsyncSession,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Handle payment.failed event."""
        payment_entity = (
            payload.get("payload", {}).get("payment", {}).get("entity")
            or payload.get("payment", {}).get("entity")
            or payload.get("payment")
            or payload
        )
        amount = float(payment_entity.get("amount", 0.0))
        # Convert paise if integer amount > 1000 and has currency INR
        if amount > 1000 and isinstance(payment_entity.get("amount"), int):
            amount = amount / 100.0

        currency = payment_entity.get("currency", "INR")
        failure_code = payment_entity.get("error_code") or payment_entity.get("failure_code") or "insufficient_funds"
        failure_message = payment_entity.get("error_description") or payment_entity.get("failure_message") or "Payment declined"
        provider_ref = payment_entity.get("id", f"pay_evt_{uuid.uuid4().hex[:8]}")

        # Customer
        cust_payload = payload.get("customer", {})
        if not cust_payload.get("email") and payment_entity.get("email"):
            cust_payload["email"] = payment_entity.get("email")
            cust_payload["name"] = payment_entity.get("contact", "Customer")
        customer = await cls._ensure_customer(session, cust_payload)

        # Create Transaction & Payment
        txn = Transaction(
            id=f"txn_{uuid.uuid4().hex[:12]}",
            customer_id=customer.id,
            amount=amount,
            currency=currency,
            status=TransactionStatus.FAILED,
            transaction_type=TransactionType.ONE_TIME,
            failure_reason=failure_code,
            provider="razorpay",
            provider_reference=provider_ref,
        )
        session.add(txn)
        await session.flush()

        payment_attempt = Payment(
            id=str(uuid.uuid4()),
            transaction_id=txn.id,
            attempt_number=1,
            status=PaymentStatus.FAILED,
            failure_code=failure_code,
            failure_message=failure_message,
        )
        session.add(payment_attempt)

        # Risk Assessment
        risk_result = RevenueRiskEngine.assess_risk(
            amount=amount,
            failure_code=failure_code,
            source_type=RecoverySourceType.PAYMENT_FAILURE,
            customer_segment=customer.segment,
            lifetime_value=customer.lifetime_value,
            past_successful_payments=3,
            failed_attempts_count=1,
        )

        # Create Recovery Case in DETECTED state
        case_id = f"RCV-{uuid.uuid4().hex[:8].upper()}"
        recovery_case = RecoveryCase(
            id=case_id,
            source_type=RecoverySourceType.PAYMENT_FAILURE,
            source_id=txn.id,
            customer_id=customer.id,
            amount_at_risk=amount,
            currency=currency,
            recovery_probability=risk_result.recovery_probability,
            priority_score=risk_result.priority_score,
            risk_category=risk_result.risk_category,
            root_cause=failure_code,
            root_cause_explanation=failure_message,
            signals_json={
                "positive": risk_result.positive_signals,
                "negative": risk_result.negative_signals,
            },
            status=RecoveryState.DETECTED,
            recovered_amount=0.0,
        )
        session.add(recovery_case)
        await session.flush()

        # Audit Log
        audit = AuditLog(
            id=str(uuid.uuid4()),
            case_id=recovery_case.id,
            actor_type=ActorType.WEBHOOK_SYSTEM,
            actor_id="webhook_dispatcher",
            action="REVENUE_RISK_DETECTED",
            reason=f"Payment failure event ingested from gateway: {failure_code}",
            metadata_json={
                "amount": amount,
                "currency": currency,
                "failure_code": failure_code,
                "priority_score": risk_result.priority_score,
            },
        )
        session.add(audit)

        return {
            "case_id": recovery_case.id,
            "status": "detected",
            "amount_at_risk": amount,
            "priority_score": risk_result.priority_score,
        }

    @classmethod
    async def _handle_payment_captured(
        cls,
        session: AsyncSession,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Handle payment.captured event and reconcile case."""
        payment_entity = payload.get("payload", {}).get("payment", {}).get("entity", payload)
        amount = float(payment_entity.get("amount", 0.0))
        if amount > 1000 and isinstance(payment_entity.get("amount"), int):
            amount = amount / 100.0

        case_id = payload.get("case_id") or payment_entity.get("notes", {}).get("case_id")
        
        if case_id:
            stmt = select(RecoveryCase).where(RecoveryCase.id == case_id)
            res = await session.execute(stmt)
            case = res.scalars().first()
            if case and case.status != RecoveryState.RECOVERED:
                case.recovered_amount = min(case.amount_at_risk, amount)
                case.status = RecoveryState.RECOVERED

                audit = AuditLog(
                    id=str(uuid.uuid4()),
                    case_id=case.id,
                    actor_type=ActorType.WEBHOOK_SYSTEM,
                    actor_id="webhook_reconciler",
                    action="PAYMENT_RECOVERED_CONFIRMED",
                    reason=f"Payment of ₹{amount:,.0f} captured successfully.",
                    metadata_json={"amount_recovered": amount, "case_id": case.id},
                )
                session.add(audit)
                return {"case_id": case.id, "status": "recovered", "amount": amount}

        return {"status": "captured_unmatched", "amount": amount}

    @classmethod
    async def _handle_subscription_failed(
        cls,
        session: AsyncSession,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Handle subscription.payment_failed event."""
        sub_entity = payload.get("payload", {}).get("subscription", {}).get("entity", payload)
        amount = float(sub_entity.get("amount", 1999.0))
        customer = await cls._ensure_customer(session, payload.get("customer", {}))

        sub = Subscription(
            id=sub_entity.get("id", f"sub_{uuid.uuid4().hex[:8]}"),
            customer_id=customer.id,
            amount=amount,
            billing_cycle=BillingCycle.MONTHLY,
            status=SubscriptionStatus.PAST_DUE,
            next_billing_at=datetime.now(timezone.utc),
            failed_attempts=1,
        )
        session.add(sub)
        await session.flush()

        risk_result = RevenueRiskEngine.assess_risk(
            amount=amount,
            failure_code="mandate_inactive",
            source_type=RecoverySourceType.SUBSCRIPTION_DUNNING,
            customer_segment=customer.segment,
            lifetime_value=customer.lifetime_value,
        )

        case_id = f"RCV-SUB-{uuid.uuid4().hex[:6].upper()}"
        recovery_case = RecoveryCase(
            id=case_id,
            source_type=RecoverySourceType.SUBSCRIPTION_DUNNING,
            source_id=sub.id,
            customer_id=customer.id,
            amount_at_risk=amount,
            recovery_probability=risk_result.recovery_probability,
            priority_score=risk_result.priority_score,
            risk_category=risk_result.risk_category,
            root_cause="subscription_mandate_failed",
            root_cause_explanation="Recurring debit authorization rejected by card issuer",
            signals_json={"positive": risk_result.positive_signals, "negative": risk_result.negative_signals},
            status=RecoveryState.DETECTED,
        )
        session.add(recovery_case)
        await session.flush()

        return {"case_id": recovery_case.id, "source_type": "SUBSCRIPTION_DUNNING", "amount": amount}

    @classmethod
    async def _handle_subscription_charged(cls, session: AsyncSession, payload: Dict[str, Any]) -> Dict[str, Any]:
        return {"status": "subscription_active", "payload": payload}

    @classmethod
    async def _handle_invoice_overdue(
        cls,
        session: AsyncSession,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Handle invoice.overdue event."""
        inv_data = payload.get("invoice", payload)
        amount = float(inv_data.get("amount", 50000.0))
        customer = await cls._ensure_customer(session, payload.get("customer", {}))

        inv = Invoice(
            id=str(uuid.uuid4()),
            customer_id=customer.id,
            invoice_number=inv_data.get("invoice_number", f"INV-{uuid.uuid4().hex[:6].upper()}"),
            amount=amount,
            due_date=datetime.now(timezone.utc) - timedelta(days=inv_data.get("overdue_days", 14)),
            status=InvoiceStatus.OVERDUE,
        )
        session.add(inv)
        await session.flush()

        risk_result = RevenueRiskEngine.assess_risk(
            amount=amount,
            failure_code="insufficient_funds",
            source_type=RecoverySourceType.OVERDUE_INVOICE,
            customer_segment=customer.segment,
            lifetime_value=customer.lifetime_value,
            invoice_age_days=inv_data.get("overdue_days", 14),
        )

        case_id = f"RCV-INV-{uuid.uuid4().hex[:6].upper()}"
        recovery_case = RecoveryCase(
            id=case_id,
            source_type=RecoverySourceType.OVERDUE_INVOICE,
            source_id=inv.id,
            customer_id=customer.id,
            amount_at_risk=amount,
            recovery_probability=risk_result.recovery_probability,
            priority_score=risk_result.priority_score,
            risk_category=risk_result.risk_category,
            root_cause="invoice_overdue",
            root_cause_explanation=f"Receivable overdue by {inv_data.get('overdue_days', 14)} days",
            signals_json={"positive": risk_result.positive_signals, "negative": risk_result.negative_signals},
            status=RecoveryState.DETECTED,
        )
        session.add(recovery_case)
        await session.flush()

        return {"case_id": recovery_case.id, "source_type": "OVERDUE_INVOICE", "amount": amount}

    @classmethod
    async def _handle_checkout_abandoned(
        cls,
        session: AsyncSession,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Handle checkout.abandoned event."""
        chk_data = payload.get("checkout", payload)
        amount = float(chk_data.get("amount", 3499.0))
        customer = await cls._ensure_customer(session, payload.get("customer", {}))

        risk_result = RevenueRiskEngine.assess_risk(
            amount=amount,
            failure_code="checkout_abandoned",
            source_type=RecoverySourceType.CHECKOUT_ABANDONMENT,
            customer_segment=customer.segment,
            lifetime_value=customer.lifetime_value,
        )

        case_id = f"RCV-CHK-{uuid.uuid4().hex[:6].upper()}"
        recovery_case = RecoveryCase(
            id=case_id,
            source_type=RecoverySourceType.CHECKOUT_ABANDONMENT,
            source_id=chk_data.get("checkout_id", f"chk_{uuid.uuid4().hex[:8]}"),
            customer_id=customer.id,
            amount_at_risk=amount,
            recovery_probability=risk_result.recovery_probability,
            priority_score=risk_result.priority_score,
            risk_category=risk_result.risk_category,
            root_cause="checkout_abandoned",
            root_cause_explanation="Customer abandoned during payment gateway checkout",
            signals_json={"positive": risk_result.positive_signals, "negative": risk_result.negative_signals},
            status=RecoveryState.DETECTED,
        )
        session.add(recovery_case)
        await session.flush()

        return {"case_id": recovery_case.id, "source_type": "CHECKOUT_ABANDONMENT", "amount": amount}
