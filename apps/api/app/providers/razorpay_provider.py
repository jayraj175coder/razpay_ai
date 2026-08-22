"""Razorpay Gateway Adapter for Live/Test mode."""
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
import httpx

from app.core.config import settings
from app.core.logging import get_logger
from app.providers.base import (
    PaymentProvider,
    PaymentResult,
    PaymentLinkResult,
    PaymentStatusResult,
)

logger = get_logger("recoverai.razorpay_provider")


class RazorpayProvider(PaymentProvider):
    """
    Razorpay API integration adapter for live/test transactions and payment links.
    """

    def __init__(
        self,
        key_id: Optional[str] = None,
        key_secret: Optional[str] = None,
        base_url: str = "https://api.razorpay.com/v1",
    ):
        self.key_id = key_id or settings.RAZORPAY_KEY_ID
        self.key_secret = key_secret or settings.RAZORPAY_KEY_SECRET
        self.base_url = base_url
        self.is_test_mode = "test" in (self.key_id or "").lower()

    async def retry_payment(
        self,
        transaction_id: str,
        amount: float,
        currency: str = "INR",
        customer_id: Optional[str] = None,
        force_outcome: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> PaymentResult:
        """Execute recurring charge or order retry via Razorpay API."""
        logger.info(f"Executing Razorpay payment retry for txn={transaction_id} amount={amount} {currency}")
        
        # When live credentials are placeholder, return structured test result
        if "placeholder" in (self.key_id or ""):
            logger.warning("Using Razorpay test fallback (placeholder credentials detected)")
            return PaymentResult(
                success=True,
                transaction_id=transaction_id,
                provider_reference=f"pay_rzp_mock_{transaction_id[:8]}",
                amount=amount,
                currency=currency,
                settled_at=datetime.now(timezone.utc),
                is_sandbox=True,
                metadata={"mode": "razorpay_test_fallback", **(metadata or {})},
            )

        # Live Razorpay HTTP request
        auth = (self.key_id, self.key_secret)
        payload = {
            "amount": int(amount * 100),  # Paise
            "currency": currency,
            "receipt": f"rcpt_{transaction_id[:16]}",
            "notes": metadata or {},
        }

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(f"{self.base_url}/orders", json=payload, auth=auth, timeout=10.0)
                if resp.status_code in [200, 201]:
                    data = resp.json()
                    return PaymentResult(
                        success=True,
                        transaction_id=transaction_id,
                        provider_reference=data.get("id", ""),
                        amount=amount,
                        currency=currency,
                        settled_at=datetime.now(timezone.utc),
                        is_sandbox=self.is_test_mode,
                        metadata=data,
                    )
                else:
                    return PaymentResult(
                        success=False,
                        transaction_id=transaction_id,
                        provider_reference="",
                        amount=amount,
                        currency=currency,
                        failure_code="api_error",
                        failure_message=resp.text,
                        is_sandbox=self.is_test_mode,
                    )
            except Exception as exc:
                return PaymentResult(
                    success=False,
                    transaction_id=transaction_id,
                    provider_reference="",
                    amount=amount,
                    currency=currency,
                    failure_code="network_error",
                    failure_message=str(exc),
                    is_sandbox=self.is_test_mode,
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
        """Create a Razorpay Standard Payment Link."""
        if "placeholder" in (self.key_id or ""):
            return PaymentLinkResult(
                success=True,
                payment_link_id="plink_rzp_mock_12345",
                short_url="https://rzp.io/i/mocktest",
                amount=amount,
                currency=currency,
                expires_at=datetime.now(timezone.utc) + timedelta(minutes=expiry_minutes),
                is_sandbox=True,
                metadata={"mode": "razorpay_test_fallback", **(metadata or {})},
            )

        auth = (self.key_id, self.key_secret)
        expire_by = int((datetime.now(timezone.utc) + timedelta(minutes=expiry_minutes)).timestamp())
        payload = {
            "amount": int(amount * 100),
            "currency": currency,
            "description": description,
            "expire_by": expire_by,
            "notes": metadata or {},
        }

        async with httpx.AsyncClient() as client:
            resp = await client.post(f"{self.base_url}/payment_links", json=payload, auth=auth, timeout=10.0)
            if resp.status_code in [200, 201]:
                data = resp.json()
                return PaymentLinkResult(
                    success=True,
                    payment_link_id=data.get("id", ""),
                    short_url=data.get("short_url", ""),
                    amount=amount,
                    currency=currency,
                    expires_at=datetime.fromtimestamp(expire_by, timezone.utc),
                    is_sandbox=self.is_test_mode,
                    metadata=data,
                )
            else:
                raise RuntimeError(f"Razorpay payment link creation failed: {resp.text}")

    async def get_payment_status(self, provider_reference: str) -> PaymentStatusResult:
        """Check live payment status from Razorpay."""
        auth = (self.key_id, self.key_secret)
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.base_url}/payments/{provider_reference}", auth=auth, timeout=10.0)
            if resp.status_code == 200:
                data = resp.json()
                return PaymentStatusResult(
                    provider_reference=provider_reference,
                    status=data.get("status", "unknown"),
                    amount=data.get("amount", 0) / 100.0,
                    currency=data.get("currency", "INR"),
                    is_sandbox=self.is_test_mode,
                    raw_response=data,
                )
            return PaymentStatusResult(
                provider_reference=provider_reference,
                status="unknown",
                amount=0.0,
                currency="INR",
                is_sandbox=self.is_test_mode,
                error_code="not_found",
            )
