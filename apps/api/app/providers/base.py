"""Abstract Payment Provider Base Class and Result Schemas."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional


@dataclass
class PaymentResult:
    success: bool
    transaction_id: str
    provider_reference: str
    amount: float
    currency: str
    failure_code: Optional[str] = None
    failure_message: Optional[str] = None
    settled_at: Optional[datetime] = None
    is_sandbox: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PaymentLinkResult:
    success: bool
    payment_link_id: str
    short_url: str
    amount: float
    currency: str
    expires_at: datetime
    is_sandbox: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PaymentStatusResult:
    provider_reference: str
    status: str  # "captured", "failed", "pending", "authorized", "refunded", "unknown"
    amount: float
    currency: str
    is_verified_captured: bool = False
    paid_at: Optional[datetime] = None
    error_code: Optional[str] = None
    error_description: Optional[str] = None
    is_sandbox: bool = True
    raw_response: Dict[str, Any] = field(default_factory=dict)


class PaymentProvider(ABC):
    """Abstract Interface for Payment Gateway Providers."""

    @abstractmethod
    async def retry_payment(
        self,
        transaction_id: str,
        amount: float,
        currency: str = "INR",
        customer_id: Optional[str] = None,
        force_outcome: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> PaymentResult:
        """Attempt to retry a failed charge or recurring debit."""
        pass

    @abstractmethod
    async def create_payment_link(
        self,
        customer_id: str,
        amount: float,
        description: str,
        currency: str = "INR",
        expiry_minutes: int = 1440,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> PaymentLinkResult:
        """Generate a hosted payment recovery link (e.g. Razorpay Payment Link)."""
        pass

    @abstractmethod
    async def get_payment_status(self, provider_reference: str) -> PaymentStatusResult:
        """Fetch real-time settlement status of a payment."""
        pass

    @abstractmethod
    async def verify_payment(self, provider_reference: str) -> PaymentStatusResult:
        """Verify payment capture and settlement against provider ledger."""
        pass
