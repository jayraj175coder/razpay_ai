"""Tests for SQLAlchemy domain models and constraints."""
import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

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
    Invoice,
    InvoiceStatus,
    RecoveryCase,
    RecoverySourceType,
    RecoveryState,
    RecoveryPolicy,
    PromiseToPay,
    PromiseStatus,
    WebhookEvent,
    WebhookStatus,
    AuditLog,
    ActorType,
)
from app.db.seed import seed_database


@pytest.mark.asyncio
async def test_customer_and_transaction_creation(db_session: AsyncSession):
    """Test creating customer and related transaction."""
    cust = Customer(
        name="Tata Consultancy Corp",
        email="finance@tatacorp.in",
        segment=CustomerSegment.ENTERPRISE,
        lifetime_value=5000000.0,
    )
    db_session.add(cust)
    await db_session.flush()

    txn = Transaction(
        customer_id=cust.id,
        amount=250000.0,
        currency="INR",
        status=TransactionStatus.FAILED,
        transaction_type=TransactionType.INVOICE,
        failure_reason="insufficient_funds",
    )
    db_session.add(txn)
    await db_session.commit()

    # Query back
    stmt = select(Customer).where(Customer.id == cust.id)
    res = await db_session.execute(stmt)
    saved_cust = res.scalars().first()
    assert saved_cust is not None
    assert saved_cust.name == "Tata Consultancy Corp"
    assert saved_cust.segment == CustomerSegment.ENTERPRISE


@pytest.mark.asyncio
async def test_recovery_case_lifecycle_model(db_session: AsyncSession):
    """Test creating recovery case and associated audit log."""
    cust = Customer(
        name="Fintech Innovators",
        email="pay@fintech.io",
        segment=CustomerSegment.SMB,
        lifetime_value=120000.0,
    )
    db_session.add(cust)
    await db_session.flush()

    case = RecoveryCase(
        id="RCV-TEST-99",
        source_type=RecoverySourceType.PAYMENT_FAILURE,
        source_id="txn_123",
        customer_id=cust.id,
        amount_at_risk=45000.0,
        recovery_probability=0.82,
        priority_score=75.0,
        status=RecoveryState.DETECTED,
    )
    db_session.add(case)
    await db_session.flush()

    audit = AuditLog(
        case_id=case.id,
        actor_type=ActorType.AI_AGENT,
        actor_id="langgraph_v1",
        action="DETECTED_RISK",
        reason="Payment failed due to 3DS timeout",
    )
    db_session.add(audit)
    await db_session.commit()

    stmt = select(RecoveryCase).where(RecoveryCase.id == "RCV-TEST-99")
    res = await db_session.execute(stmt)
    saved_case = res.scalars().first()
    assert saved_case is not None
    assert saved_case.amount_at_risk == 45000.0
    assert saved_case.status == RecoveryState.DETECTED


@pytest.mark.asyncio
async def test_webhook_event_idempotency_constraint(db_session: AsyncSession):
    """Test that duplicate webhook events with same provider, event_id, and payload_hash are rejected."""
    evt1 = WebhookEvent(
        provider="razorpay",
        event_id="evt_test_12345",
        event_type="payment.failed",
        payload_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        payload={"event": "payment.failed", "id": "evt_test_12345"},
        status=WebhookStatus.RECEIVED,
    )
    db_session.add(evt1)
    await db_session.commit()

    # Attempt inserting duplicate
    evt2 = WebhookEvent(
        provider="razorpay",
        event_id="evt_test_12345",
        event_type="payment.failed",
        payload_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        payload={"event": "payment.failed", "id": "evt_test_12345"},
        status=WebhookStatus.RECEIVED,
    )
    db_session.add(evt2)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_database_seeding(db_session: AsyncSession):
    """Test seed_database populates policies, customers, and cases."""
    await seed_database(db_session)

    # Check policy
    stmt_policy = select(RecoveryPolicy)
    res_policy = await db_session.execute(stmt_policy)
    policies = res_policy.scalars().all()
    assert len(policies) >= 1
    assert policies[0].max_payment_retries == 3

    # Check cases
    stmt_cases = select(RecoveryCase)
    res_cases = await db_session.execute(stmt_cases)
    cases = res_cases.scalars().all()
    assert len(cases) >= 4
