"""Unit tests for Payment Gateway Providers."""
import pytest
from app.providers.factory import get_payment_provider
from app.providers.mock_provider import MockPaymentProvider
from app.providers.razorpay_provider import RazorpayProvider


@pytest.mark.asyncio
async def test_mock_payment_retry_success():
    """Test mock retry with forced success outcome."""
    provider = MockPaymentProvider()
    result = await provider.retry_payment(
        transaction_id="txn_test_123",
        amount=15000.0,
        currency="INR",
        force_outcome="SUCCESS",
    )
    assert result.success is True
    assert result.amount == 15000.0
    assert result.currency == "INR"
    assert result.is_sandbox is True
    assert result.provider_reference.startswith("pay_mock_")
    assert result.settled_at is not None


@pytest.mark.asyncio
async def test_mock_payment_retry_failure():
    """Test mock retry with forced failure outcome."""
    provider = MockPaymentProvider()
    result = await provider.retry_payment(
        transaction_id="txn_test_456",
        amount=25000.0,
        currency="INR",
        force_outcome="FAILED",
    )
    assert result.success is False
    assert result.failure_code is not None
    assert result.failure_message is not None
    assert result.is_sandbox is True


@pytest.mark.asyncio
async def test_mock_payment_link_generation():
    """Test payment link generation."""
    provider = MockPaymentProvider()
    result = await provider.create_payment_link(
        customer_id="cust_123",
        amount=4999.0,
        description="Invoice #INV-2026-001 Recovery Link",
        expiry_minutes=120,
    )
    assert result.success is True
    assert result.short_url.startswith("https://rzp.io/i/")
    assert result.amount == 4999.0
    assert result.is_sandbox is True
    assert result.expires_at is not None


@pytest.mark.asyncio
async def test_mock_get_payment_status():
    """Test payment status retrieval."""
    provider = MockPaymentProvider()
    status = await provider.get_payment_status("pay_mock_12345")
    assert status.status == "captured"
    assert status.is_sandbox is True


def test_provider_factory():
    """Test provider factory resolution."""
    mock_p = get_payment_provider("mock")
    assert isinstance(mock_p, MockPaymentProvider)

    rzp_p = get_payment_provider("razorpay")
    assert isinstance(rzp_p, RazorpayProvider)
