"""Factory for retrieving configured payment provider instance."""
from typing import Optional
from app.core.config import settings
from app.providers.base import PaymentProvider
from app.providers.mock_provider import MockPaymentProvider
from app.providers.razorpay_provider import RazorpayProvider


def get_payment_provider(provider_name: Optional[str] = None) -> PaymentProvider:
    """Return the instantiated PaymentProvider matching configuration."""
    name = (provider_name or settings.PAYMENT_PROVIDER).lower().strip()
    if name == "razorpay":
        return RazorpayProvider()
    return MockPaymentProvider()
