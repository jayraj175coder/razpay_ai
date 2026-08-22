"""Database seeder with realistic Indian fintech test dataset."""
import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal, engine, Base
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
    RiskCategory,
    RecoveryAction,
    RecoveryActionType,
    PolicyDecision,
    ActionExecutionStatus,
    RecoveryPolicy,
    PromiseToPay,
    PromiseStatus,
    AuditLog,
    ActorType,
)


async def seed_database(session: AsyncSession) -> None:
    """Populate database with realistic demo cases."""
    # Check if policy exists
    stmt = select(RecoveryPolicy).limit(1)
    res = await session.execute(stmt)
    if res.scalars().first() is not None:
        return  # Already seeded

    # 1. Create Default Recovery Policy v1
    default_policy = RecoveryPolicy(
        id=str(uuid.uuid4()),
        name="Enterprise Standard Recovery Policy",
        version=1,
        is_active=True,
        max_payment_retries=3,
        max_messages=2,
        communication_window_hours=168,
        max_discount_pct=5.0,
        human_approval_threshold=100000.0,  # ₹1,00,000 threshold
        retry_delay_hours=24,
        escalation_delay_hours=72,
        rules_json={
            "disallowed_failure_codes": ["fraud_suspected", "stolen_card", "account_frozen"],
            "high_value_escalate_threshold": 100000.0,
            "min_days_between_reminders": 3,
        },
        created_at=datetime.now(timezone.utc),
    )
    session.add(default_policy)

    # 2. Customers
    c1 = Customer(
        id="cust_enterprise_01",
        name="Nexus Cloud Technologies Pvt Ltd",
        email="finance@nexuscloud.in",
        phone="+919876543210",
        segment=CustomerSegment.ENTERPRISE,
        lifetime_value=1450000.0,  # ₹14.5 Lakhs
        created_at=datetime.now(timezone.utc) - timedelta(days=180),
    )
    c2 = Customer(
        id="cust_smb_02",
        name="Zenscale Logistics LLP",
        email="accounts@zenscale.co",
        phone="+919811223344",
        segment=CustomerSegment.SMB,
        lifetime_value=280000.0,  # ₹2.8 Lakhs
        created_at=datetime.now(timezone.utc) - timedelta(days=90),
    )
    c3 = Customer(
        id="cust_vip_03",
        name="Kaveri Retail Ventures",
        email="billing@kaveriretail.com",
        phone="+919700112233",
        segment=CustomerSegment.VIP,
        lifetime_value=620000.0,  # ₹6.2 Lakhs
        created_at=datetime.now(timezone.utc) - timedelta(days=120),
    )
    c4 = Customer(
        id="cust_retail_04",
        name="Rohan Sharma",
        email="rohan.sharma.dev@gmail.com",
        phone="+919988776655",
        segment=CustomerSegment.RETAIL,
        lifetime_value=45000.0,  # ₹45k
        created_at=datetime.now(timezone.utc) - timedelta(days=45),
    )
    c_acme = Customer(
        id="cust_acme_golden",
        name="Acme Pvt Ltd",
        email="finance@acme.in",
        phone="+919820011223",
        segment=CustomerSegment.VIP,
        lifetime_value=850000.0,  # ₹8.5 Lakhs
        created_at=datetime.now(timezone.utc) - timedelta(days=150),
    )
    session.add_all([c1, c2, c3, c4, c_acme])
    await session.flush()

    # 3. Transactions & Invoices
    # Past successful transactions for historical track record
    t1_hist = Transaction(
        id="txn_succ_01",
        customer_id=c1.id,
        amount=250000.0,
        currency="INR",
        status=TransactionStatus.SUCCESS,
        transaction_type=TransactionType.INVOICE,
        provider="razorpay",
        provider_reference="pay_settled_01",
        created_at=datetime.now(timezone.utc) - timedelta(days=30),
    )
    t2_hist = Transaction(
        id="txn_succ_02",
        customer_id=c2.id,
        amount=24500.0,
        currency="INR",
        status=TransactionStatus.SUCCESS,
        transaction_type=TransactionType.SUBSCRIPTION,
        provider="razorpay",
        provider_reference="pay_settled_02",
        created_at=datetime.now(timezone.utc) - timedelta(days=35),
    )
    t3_hist = Transaction(
        id="txn_succ_03",
        customer_id=c3.id,
        amount=85000.0,
        currency="INR",
        status=TransactionStatus.SUCCESS,
        transaction_type=TransactionType.ONE_TIME,
        provider="razorpay",
        provider_reference="pay_settled_03",
        created_at=datetime.now(timezone.utc) - timedelta(days=60),
    )

    # 14 Historical successful payments for Acme Pvt Ltd
    acme_past_txns = [
        Transaction(
            id=f"txn_acme_succ_{i+1:02d}",
            customer_id=c_acme.id,
            amount=60000.0,
            currency="INR",
            status=TransactionStatus.SUCCESS,
            transaction_type=TransactionType.SUBSCRIPTION,
            provider="razorpay",
            provider_reference=f"pay_acme_settled_{i+1:02d}",
            created_at=datetime.now(timezone.utc) - timedelta(days=150 - (i * 10)),
        )
        for i in range(14)
    ]
    # 2 Past transient failures for Acme
    acme_fail_1 = Transaction(
        id="txn_acme_fail_01",
        customer_id=c_acme.id,
        amount=85000.0,
        currency="INR",
        status=TransactionStatus.FAILED,
        transaction_type=TransactionType.SUBSCRIPTION,
        failure_reason="network_timeout",
        provider="razorpay",
        provider_reference="pay_acme_fail_01",
        created_at=datetime.now(timezone.utc) - timedelta(days=2),
    )
    acme_fail_2 = Transaction(
        id="txn_acme_fail_02",
        customer_id=c_acme.id,
        amount=85000.0,
        currency="INR",
        status=TransactionStatus.FAILED,
        transaction_type=TransactionType.SUBSCRIPTION,
        failure_reason="gateway_error",
        provider="razorpay",
        provider_reference="pay_acme_fail_02",
        created_at=datetime.now(timezone.utc) - timedelta(days=1),
    )
    # Active Golden Transaction
    t_golden = Transaction(
        id="txn_golden_acme_85k",
        customer_id=c_acme.id,
        amount=85000.0,
        currency="INR",
        status=TransactionStatus.FAILED,
        transaction_type=TransactionType.SUBSCRIPTION,
        failure_reason="network_timeout",
        provider="razorpay",
        provider_reference="pay_golden_acme_init",
        created_at=datetime.now(timezone.utc) - timedelta(hours=3),
    )

    t1 = Transaction(
        id="txn_fail_01",
        customer_id=c1.id,
        amount=125000.0,  # ₹1,25,000 (Requires human approval)
        currency="INR",
        status=TransactionStatus.FAILED,
        transaction_type=TransactionType.INVOICE,
        failure_reason="insufficient_funds",
        provider="razorpay",
        provider_reference="pay_Q8aL9k12345",
        created_at=datetime.now(timezone.utc) - timedelta(hours=6),
    )
    t2 = Transaction(
        id="txn_fail_02",
        customer_id=c2.id,
        amount=24500.0,  # ₹24,500
        currency="INR",
        status=TransactionStatus.FAILED,
        transaction_type=TransactionType.SUBSCRIPTION,
        failure_reason="network_timeout",
        provider="razorpay",
        provider_reference="pay_B7nM3k54321",
        created_at=datetime.now(timezone.utc) - timedelta(hours=14),
    )
    t3 = Transaction(
        id="txn_fail_03",
        customer_id=c3.id,
        amount=85000.0,  # ₹85,000
        currency="INR",
        status=TransactionStatus.FAILED,
        transaction_type=TransactionType.ONE_TIME,
        failure_reason="card_expired",
        provider="razorpay",
        provider_reference="pay_K9vC2x98765",
        created_at=datetime.now(timezone.utc) - timedelta(hours=22),
    )
    t4 = Transaction(
        id="txn_fail_04",
        customer_id=c4.id,
        amount=7999.0,  # ₹7,999
        currency="INR",
        status=TransactionStatus.FAILED,
        transaction_type=TransactionType.CHECKOUT,
        failure_reason="auth_failed",
        provider="razorpay",
        provider_reference="pay_R4tZ8m11223",
        created_at=datetime.now(timezone.utc) - timedelta(hours=2),
    )

    # Invoices
    inv1 = Invoice(
        id="inv_enterprise_01",
        customer_id=c1.id,
        invoice_number="INV-2026-NX01",
        amount=125000.0,
        currency="INR",
        status=InvoiceStatus.OVERDUE,
        due_date=datetime.now(timezone.utc) - timedelta(days=5),
        created_at=datetime.now(timezone.utc) - timedelta(days=35),
    )
    session.add_all([t1_hist, t2_hist, t3_hist, *acme_past_txns, acme_fail_1, acme_fail_2, t_golden, t1, t2, t3, t4, inv1])
    await session.flush()

    # Payments attempts
    p1 = Payment(
        id=str(uuid.uuid4()),
        transaction_id=t1.id,
        attempt_number=1,
        status=PaymentStatus.FAILED,
        failure_code="insufficient_funds",
        failure_message="Bank declined transaction due to temporary balance limits",
        attempted_at=datetime.now(timezone.utc) - timedelta(hours=6),
    )
    p2 = Payment(
        id=str(uuid.uuid4()),
        transaction_id=t2.id,
        attempt_number=1,
        status=PaymentStatus.FAILED,
        failure_code="network_timeout",
        failure_message="Issuer bank gateway timeout during 3D Secure verification",
        attempted_at=datetime.now(timezone.utc) - timedelta(hours=14),
    )
    p3 = Payment(
        id=str(uuid.uuid4()),
        transaction_id=t3.id,
        attempt_number=1,
        status=PaymentStatus.FAILED,
        failure_code="card_expired",
        failure_message="Card validity expired (MM/YY)",
        attempted_at=datetime.now(timezone.utc) - timedelta(hours=22),
    )
    p4 = Payment(
        id=str(uuid.uuid4()),
        transaction_id=t4.id,
        attempt_number=1,
        status=PaymentStatus.FAILED,
        failure_code="auth_failed",
        failure_message="User did not complete OTP challenge on checkout page",
        attempted_at=datetime.now(timezone.utc) - timedelta(hours=2),
    )
    session.add_all([p1, p2, p3, p4])

    # 4. Recovery Cases
    # Case 1: High value invoice dunning (Requires Human Approval)
    rc1 = RecoveryCase(
        id="RCV-NX-1001",
        source_type=RecoverySourceType.OVERDUE_INVOICE,
        source_id=t1.id,
        customer_id=c1.id,
        amount_at_risk=125000.0,
        currency="INR",
        recovery_probability=0.88,
        priority_score=92.5,
        risk_category=RiskCategory.CRITICAL,
        root_cause="temporary_insufficient_funds",
        root_cause_explanation="Enterprise customer with 100% past payment fulfillment experiencing quarter-end balance sweep delay.",
        recommended_action="SCHEDULE_CALL",
        recommended_channel="PHONE_ESCALATION",
        ai_reasoning="High LTV Enterprise client (₹14.5L LTV). Automated cold retries might damage relationship. Safe approach is relationship manager call with human signoff.",
        signals_json={
            "positive": [
                "+ ₹14,50,000 Historical Lifetime Value across 18 transactions",
                "+ 100% on-time settlement history in preceding 6 quarters",
                "+ Active SaaS contract with multi-year lockin",
            ],
            "negative": [
                "- Large transaction amount (₹1,25,000) exceeds auto-retry safety threshold",
                "- End of month bank balance sweep",
            ],
        },
        status=RecoveryState.POLICY_CHECK,
        recovered_amount=0.0,
        created_at=datetime.now(timezone.utc) - timedelta(hours=6),
    )

    # Case 2: Subscription Dunning (Auto-Retry Scheduled)
    rc2 = RecoveryCase(
        id="RCV-ZS-1002",
        source_type=RecoverySourceType.SUBSCRIPTION_DUNNING,
        source_id=t2.id,
        customer_id=c2.id,
        amount_at_risk=24500.0,
        currency="INR",
        recovery_probability=0.94,
        priority_score=81.0,
        risk_category=RiskCategory.HIGH,
        root_cause="transient_gateway_timeout",
        root_cause_explanation="Bank network downtime during recurring debit batch.",
        recommended_action="RETRY_PAYMENT",
        recommended_channel="SMART_RETRY",
        ai_reasoning="Transient infrastructure timeout with 0 funds/credit deficiency signals. Smart off-peak auto-retry recommended within policy limits.",
        signals_json={
            "positive": [
                "+ 9 consecutive successful monthly subscription renewals",
                "+ Gateway error code confirms interbank network timeout, not customer delinquency",
                "+ Low risk category",
            ],
            "negative": [
                "- Recurring mandate attempt 1 failed",
            ],
        },
        status=RecoveryState.RETRY_SCHEDULED,
        recovered_amount=0.0,
        created_at=datetime.now(timezone.utc) - timedelta(hours=14),
    )

    # Case 3: Expired Card with Promise-to-Pay
    rc3 = RecoveryCase(
        id="RCV-KV-1003",
        source_type=RecoverySourceType.PAYMENT_FAILURE,
        source_id=t3.id,
        customer_id=c3.id,
        amount_at_risk=85000.0,
        currency="INR",
        recovery_probability=0.85,
        priority_score=87.0,
        risk_category=RiskCategory.HIGH,
        root_cause="card_expired",
        root_cause_explanation="Primary corporate credit card expired last month.",
        recommended_action="CREATE_PAYMENT_LINK",
        recommended_channel="WHATSAPP",
        ai_reasoning="Card expired. Customer promised payment after replacement card activation.",
        signals_json={
            "positive": [
                "+ Customer proactively responded with promise to pay",
                "+ ₹6,20,000 proven historical spend",
            ],
            "negative": [
                "- Card expired, auto-retry will fail deterministically",
            ],
        },
        status=RecoveryState.EXECUTING,
        recovered_amount=0.0,
        created_at=datetime.now(timezone.utc) - timedelta(hours=22),
    )

    # Case 4: Checkout Abandonment Recovered
    rc4 = RecoveryCase(
        id="RCV-RS-1004",
        source_type=RecoverySourceType.CHECKOUT_ABANDONMENT,
        source_id=t4.id,
        customer_id=c4.id,
        amount_at_risk=7999.0,
        currency="INR",
        recovery_probability=0.91,
        priority_score=68.0,
        risk_category=RiskCategory.MEDIUM,
        root_cause="checkout_dropoff_otp",
        root_cause_explanation="User abandoned checkout at OTP stage due to SMS delay.",
        recommended_action="SEND_PAYMENT_REMINDER",
        recommended_channel="EMAIL",
        ai_reasoning="Delivered personalized recovery payment link with 1-click cart restore.",
        signals_json={
            "positive": [
                "+ User completed payment link within 45 minutes of reminder",
                "+ Cart items preserved",
            ],
            "negative": [],
        },
        status=RecoveryState.RECOVERED,
        recovered_amount=7999.0,
        created_at=datetime.now(timezone.utc) - timedelta(hours=2),
    )

    # Golden Demo Case: Acme Pvt Ltd (₹85,000, 14 successful payments, 2 recent failures)
    rc_golden = RecoveryCase(
        id="RCV-ACME-85K",
        source_type=RecoverySourceType.SUBSCRIPTION_DUNNING,
        source_id=t_golden.id,
        customer_id=c_acme.id,
        amount_at_risk=85000.0,
        currency="INR",
        recovery_probability=0.87,
        priority_score=88.5,
        risk_category=RiskCategory.HIGH,
        root_cause="network_timeout",
        root_cause_explanation="Temporary bank gateway timeout on recurring subscription charge.",
        recommended_action="RETRY_PAYMENT",
        recommended_channel="SMART_RETRY",
        ai_reasoning="Strong historical track record (14 past settlements). Transient network timeout is fully recoverable via off-peak smart retry.",
        signals_json={
            "positive": [
                "+ 14 previous successful payments on record",
                "+ High LTV VIP Customer (₹8,50,000)",
                "+ Transient failure type (network_timeout)",
            ],
            "negative": [
                "- 2 recent failed attempts during bank server peak downtime",
            ],
        },
        status=RecoveryState.DETECTED,
        recovered_amount=0.0,
        created_at=datetime.now(timezone.utc) - timedelta(hours=3),
    )

    session.add_all([rc1, rc2, rc3, rc4, rc_golden])
    await session.flush()

    # 5. Promise to pay for Case 3
    prom1 = PromiseToPay(
        id=str(uuid.uuid4()),
        recovery_case_id=rc3.id,
        customer_id=c3.id,
        promised_amount=85000.0,
        promise_date=datetime.now(timezone.utc) + timedelta(days=2),
        confidence=0.95,
        raw_text="Our new corporate card is being delivered tomorrow, will pay the full ₹85,000 invoice by Wednesday afternoon.",
        status=PromiseStatus.WAITING,
        created_at=datetime.now(timezone.utc) - timedelta(hours=10),
    )
    session.add(prom1)

    # 6. Audit Logs
    audit1 = AuditLog(
        id=str(uuid.uuid4()),
        case_id=rc1.id,
        actor_type=ActorType.AI_AGENT,
        actor_id="langgraph_agent_v1",
        action="DIAGNOSIS_COMPLETED",
        reason="Identified temporary liquidity timing based on LTV and historical records",
        metadata_json={"confidence": 0.91, "risk_category": "CRITICAL"},
        created_at=datetime.now(timezone.utc) - timedelta(hours=5, minutes=58),
    )
    audit2 = AuditLog(
        id=str(uuid.uuid4()),
        case_id=rc1.id,
        actor_type=ActorType.POLICY_ENGINE,
        actor_id="policy_engine_v1",
        action="POLICY_GATE_TRIGGERED",
        reason="Amount ₹1,25,000 exceeds automatic execution threshold of ₹1,00,000. Human approval required.",
        metadata_json={"threshold": 100000.0, "amount": 125000.0, "decision": "REQUIRES_HUMAN_APPROVAL"},
        created_at=datetime.now(timezone.utc) - timedelta(hours=5, minutes=55),
    )
    audit3 = AuditLog(
        id=str(uuid.uuid4()),
        case_id=rc4.id,
        actor_type=ActorType.RECOVERY_EXECUTOR,
        actor_id="payment_provider_sandbox",
        action="PAYMENT_VERIFIED",
        reason="Payment link captured ₹7,999 successfully via UPI",
        metadata_json={"amount": 7999.0, "payment_method": "upi", "settlement": "instant"},
        created_at=datetime.now(timezone.utc) - timedelta(hours=1),
    )
    session.add_all([audit1, audit2, audit3])

    await session.commit()


async def init_and_seed():
    """Create tables and seed data if empty."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with AsyncSessionLocal() as session:
        await seed_database(session)


if __name__ == "__main__":
    asyncio.run(init_and_seed())
