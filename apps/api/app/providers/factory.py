"""Factory for retrieving configured payment provider instance."""
from typing import Optional
from app.core.config import settings
from app.core.logging import get_logger
from app.providers.base import PaymentProvider
from app.providers.mock_provider import MockPaymentProvider
from app.providers.razorpay_provider import RazorpayProvider

logger = get_logger("recoverai.providers.factory")


def get_payment_provider(provider_name: Optional[str] = None) -> PaymentProvider:
    """
    Return the instantiated PaymentProvider matching configuration.
    If Razorpay is selected without credentials, falls back cleanly to Mock sandbox.
    """
    name = (provider_name or settings.PAYMENT_PROVIDER).lower().strip()
    if name == "razorpay":
        key_id = settings.RAZORPAY_KEY_ID
        if key_id and "placeholder" not in key_id.lower() and key_id.startswith("rzp_"):
            return RazorpayProvider()
        else:
            logger.info("Razorpay credentials not set; initializing MockPaymentProvider in Sandbox Mode")
            return MockPaymentProvider()
    return MockPaymentProvider()
