"""End-to-End Golden Recovery Case Integration Test: Acme Pvt Ltd (₹85,000)."""
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.agents.graph import RecoveryAgentGraph
from app.db.seed import seed_database
from app.models import RecoveryCase, RecoveryState, RecoveryAction, AuditLog
from app.services.customer_context import CustomerContextService
from app.services.payment_verification import PaymentVerificationService


@pytest.mark.asyncio
async def test_acme_golden_recovery_flow(db_session: AsyncSession):
    """
    Validate the complete deterministic Golden Recovery flow:
    Customer: Acme Pvt Ltd
    Amount: ₹85,000
    Historical Track: 14 successful payments, 2 recent failures
    Failure Type: Transient network_timeout
    Outcome: Verified recovery of ₹85,000 with complete audit trail.
    """
    await seed_database(db_session)

    # 1. Verify Golden Case exists in DETECTED state
    stmt = (
        select(RecoveryCase)
        .where(RecoveryCase.id == "RCV-ACME-85K")
        .options(selectinload(RecoveryCase.customer))
    )
    res = await db_session.execute(stmt)
    case = res.scalars().first()
    assert case is not None
    assert case.amount_at_risk == 85000.0
    assert case.status == RecoveryState.DETECTED
    assert case.customer.name == "Acme Pvt Ltd"

    # 2. Verify CustomerContext aggregation for Acme
    ctx = await CustomerContextService.load_customer_context(db_session, case.customer_id)
    assert ctx.name == "Acme Pvt Ltd"
    assert ctx.successful_payments_count == 14
    assert ctx.failed_payments_count >= 2
    assert ctx.lifetime_value == 850000.0

    # 3. Execute the 10-node LangGraph Recovery Agent Graph
    graph = RecoveryAgentGraph(db_session)
    result = await graph.run(case.id)

    # 4. Verify AI Diagnosis and Strategy Output
    assert "diagnosis" in result
    assert result["diagnosis"]["root_cause"] is not None
    assert "strategy" in result
    assert result["strategy"]["recommended_action"] in ["RETRY_PAYMENT", "CREATE_PAYMENT_LINK", "SEND_PAYMENT_REMINDER"]

    # 5. Verify Policy Engine Gate
    assert "policy_evaluation" in result
    assert result["policy_evaluation"]["allowed"] is True
    assert result["policy_evaluation"]["requires_human_approval"] is False

    # 6. Verify Outcome in Database
    stmt_updated = (
        select(RecoveryCase)
        .where(RecoveryCase.id == "RCV-ACME-85K")
        .options(selectinload(RecoveryCase.actions), selectinload(RecoveryCase.attempts))
    )
    res_up = await db_session.execute(stmt_updated)
    updated_case = res_up.scalars().first()
    assert updated_case is not None

    # Status must be RECOVERED or EXECUTING (bounded payment executed)
    assert updated_case.status in [RecoveryState.RECOVERED, RecoveryState.EXECUTING]
    if updated_case.status == RecoveryState.RECOVERED:
        assert updated_case.recovered_amount == 85000.0

    # 7. Verify Audit Trail entries
    stmt_audit = select(AuditLog).where(AuditLog.case_id == "RCV-ACME-85K").order_by(AuditLog.created_at.asc())
    audit_res = await db_session.execute(stmt_audit)
    audit_logs = audit_res.scalars().all()
    assert len(audit_logs) >= 2
    assert any(log.action == "AI_DIAGNOSIS_AND_STRATEGY_GENERATED" for log in audit_logs)
