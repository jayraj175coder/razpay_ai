"""Tests for Webhook Event Ingestion and Idempotency."""
import json
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import RecoveryCase, RecoveryState, WebhookEvent, WebhookStatus


@pytest.mark.asyncio
async def test_payment_failed_webhook_creates_case(client: AsyncClient, db_session: AsyncSession):
    """Test payment.failed webhook generates recovery case in DETECTED state."""
    payload = {
        "id": "evt_test_failed_101",
        "event": "payment.failed",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_test_failed_101",
                    "amount": 2500000,  # ₹25,000 in paise
                    "currency": "INR",
                    "error_code": "insufficient_funds",
                    "error_description": "Declined by issuing bank",
                    "email": "priya.patel@zenscale.in",
                    "contact": "+919876500112",
                }
            }
        },
        "customer": {
            "name": "Priya Patel",
            "email": "priya.patel@zenscale.in",
            "segment": "SMB",
            "lifetime_value": 150000.0,
        },
    }

    response = await client.post("/api/v1/webhooks/razorpay", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["duplicate"] is False
    assert data["data"]["status"] == "detected"
    assert data["data"]["amount_at_risk"] == 25000.0

    # Query DB
    case_id = data["data"]["case_id"]
    stmt = select(RecoveryCase).where(RecoveryCase.id == case_id)
    res = await db_session.execute(stmt)
    case = res.scalars().first()
    assert case is not None
    assert case.status == RecoveryState.DETECTED
    assert case.amount_at_risk == 25000.0


@pytest.mark.asyncio
async def test_duplicate_webhook_rejection_idempotency(client: AsyncClient):
    """Test duplicate webhook delivery is rejected idempotently with duplicate=True."""
    payload = {
        "event_id": "evt_idempotent_999",
        "event": "payment.failed",
        "amount": 10000.0,
        "failure_code": "network_timeout",
        "customer": {
            "name": "Anil Kumar",
            "email": "anil.k@example.com",
            "segment": "RETAIL",
        },
    }

    # First attempt
    res1 = await client.post("/api/v1/webhooks/simulate", json=payload)
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["duplicate"] is False

    # Second identical attempt
    res2 = await client.post("/api/v1/webhooks/simulate", json=payload)
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["duplicate"] is True
    assert "Duplicate" in data2["message"]


@pytest.mark.asyncio
async def test_checkout_abandoned_webhook(client: AsyncClient):
    """Test checkout.abandoned creates recovery case."""
    payload = {
        "event": "checkout.abandoned",
        "checkout": {
            "checkout_id": "chk_cart_888",
            "amount": 4999.0,
        },
        "customer": {
            "name": "Sneha Roy",
            "email": "sneha.roy@gmail.com",
            "segment": "RETAIL",
        },
    }
    response = await client.post("/api/v1/webhooks/simulate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["source_type"] == "CHECKOUT_ABANDONMENT"
