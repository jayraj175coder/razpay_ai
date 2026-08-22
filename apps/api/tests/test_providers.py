"""Unit tests for Payment Gateway Providers and Verification."""
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

    # Verify status lookup
    v_status = await provider.verify_payment(result.provider_reference)
    assert v_status.is_verified_captured is True
    assert v_status.status == "captured"


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

    # Verify status lookup
    v_status = await provider.verify_payment(result.provider_reference)
    assert v_status.is_verified_captured is False
    assert v_status.status == "failed"


@pytest.mark.asyncio
async def test_mock_payment_deterministic_overrides():
    """Test deterministic test fixture overrides."""
    provider = MockPaymentProvider()
    res1 = await provider.retry_payment(transaction_id="PAY-001", amount=5000.0)
    assert res1.success is True

    res2 = await provider.retry_payment(transaction_id="PAY-002", amount=5000.0)
    assert res2.success is False


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
async def test_razorpay_provider_unconfigured_error():
    """Test RazorpayProvider raises explicit error when credentials unconfigured."""
    provider = RazorpayProvider(key_id="rzp_test_placeholder", key_secret="placeholder")
    with pytest.raises(RuntimeError, match="credentials are not configured"):
        await provider.retry_payment(transaction_id="txn_test", amount=1000.0)


def test_provider_factory():
    """Test provider factory resolution."""
    mock_p = get_payment_provider("mock")
    assert isinstance(mock_p, MockPaymentProvider)

    # When placeholder in config, factory cleanly falls back to Mock sandbox
    default_p = get_payment_provider()
    assert isinstance(default_p, MockPaymentProvider)
