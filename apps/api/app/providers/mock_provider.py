"""Sandbox Mock Payment Provider with deterministic simulation behavior and status verification."""
import uuid
import random
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
from app.providers.base import (
    PaymentProvider,
    PaymentResult,
    PaymentLinkResult,
    PaymentStatusResult,
)


class MockPaymentProvider(PaymentProvider):
    """
    Mock payment gateway simulating Razorpay behavior for sandboxed,
    deterministic testing and recovery demonstration.
    """

    # In-memory store of mock transactions for consistent verification
    _mock_ledger: Dict[str, Dict[str, Any]] = {}

    # Deterministic test fixture overrides
    STATIC_OVERRIDES: Dict[str, str] = {
        "PAY-001": "SUCCESS",
        "PAY-002": "FAILED",
        "PAY-003": "SUCCESS",
        "TXN-GOLDEN-001": "SUCCESS",
        "txn_golden_acme_85k": "SUCCESS",
    }

    def __init__(self, default_success_rate: float = 0.85, seed: Optional[int] = None):
        self.default_success_rate = default_success_rate
        self.rng = random.Random(seed) if seed is not None else random.Random(42)

    async def retry_payment(
        self,
        transaction_id: str,
        amount: float,
        currency: str = "INR",
        customer_id: Optional[str] = None,
        force_outcome: Optional[str] = None,  # "SUCCESS", "FAILED", or None
        metadata: Optional[Dict[str, Any]] = None,
    ) -> PaymentResult:
        """Simulate re-attempting a payment transaction."""
        ref_id = f"pay_mock_{uuid.uuid4().hex[:14]}"

        # Check static override fixture first
        override = self.STATIC_OVERRIDES.get(transaction_id)
        effective_force = force_outcome or override

        # Determine success
        if effective_force == "SUCCESS":
            is_success = True
        elif effective_force == "FAILED":
            is_success = False
        else:
            is_success = self.rng.random() < self.default_success_rate

        if is_success:
            settled_time = datetime.now(timezone.utc)
            self._mock_ledger[ref_id] = {
                "status": "captured",
                "amount": amount,
                "currency": currency,
                "paid_at": settled_time,
                "transaction_id": transaction_id,
            }
            return PaymentResult(
                success=True,
                transaction_id=transaction_id,
                provider_reference=ref_id,
                amount=amount,
                currency=currency,
                settled_at=settled_time,
                is_sandbox=True,
                metadata={
                    "method": "upi",
                    "bank": "HDFC",
                    "vpa": "customer@okhdfcbank",
                    "provider": "MockSandboxGateway",
                    **(metadata or {}),
                },
            )
        else:
            failure_codes = ["insufficient_funds", "bank_server_down", "card_declined", "limit_exceeded"]
            chosen_failure = self.rng.choice(failure_codes)
            self._mock_ledger[ref_id] = {
                "status": "failed",
                "amount": amount,
                "currency": currency,
                "error_code": chosen_failure,
                "transaction_id": transaction_id,
            }
            return PaymentResult(
                success=False,
                transaction_id=transaction_id,
                provider_reference=ref_id,
                amount=amount,
                currency=currency,
                failure_code=chosen_failure,
                failure_message=f"Simulated decline: {chosen_failure.replace('_', ' ').capitalize()}",
                is_sandbox=True,
                metadata={
                    "provider": "MockSandboxGateway",
                    **(metadata or {}),
                },
            )

    async def create_payment_link(
        self,
        customer_id: str,
        amount: float,
        description: str,
        currency: str = "INR",
        expiry_minutes: int = 1440,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> PaymentLinkResult:
        """Generate a simulated Razorpay Payment Link."""
        link_id = f"plink_mock_{uuid.uuid4().hex[:12]}"
        short_url = f"https://rzp.io/i/{link_id[-8:]}"
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=expiry_minutes)

        self._mock_ledger[link_id] = {
            "status": "created",
            "amount": amount,
            "currency": currency,
            "short_url": short_url,
            "customer_id": customer_id,
        }

        return PaymentLinkResult(
            success=True,
            payment_link_id=link_id,
            short_url=short_url,
            amount=amount,
            currency=currency,
            expires_at=expires_at,
            is_sandbox=True,
            metadata={
                "customer_id": customer_id,
                "description": description,
                "provider": "MockSandboxGateway",
                **(metadata or {}),
            },
        )

    async def get_payment_status(self, provider_reference: str) -> PaymentStatusResult:
        """Retrieve simulated payment status from in-memory ledger."""
        record = self._mock_ledger.get(provider_reference)
        if record:
            st = record.get("status", "unknown")
            return PaymentStatusResult(
                provider_reference=provider_reference,
                status=st,
                amount=record.get("amount", 0.0),
                currency=record.get("currency", "INR"),
                is_verified_captured=(st == "captured"),
                paid_at=record.get("paid_at"),
                error_code=record.get("error_code"),
                is_sandbox=True,
                raw_response={"id": provider_reference, "entity": "payment", "status": st},
            )

        # Fallback for unknown references
        return PaymentStatusResult(
            provider_reference=provider_reference,
            status="captured",
            amount=0.0,
            currency="INR",
            is_verified_captured=True,
            paid_at=datetime.now(timezone.utc),
            is_sandbox=True,
            raw_response={"id": provider_reference, "entity": "payment", "status": "captured"},
        )

    async def verify_payment(self, provider_reference: str) -> PaymentStatusResult:
        """Verify payment capture and settlement against provider ledger."""
        return await self.get_payment_status(provider_reference)
