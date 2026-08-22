"""Unit and integration tests for LangGraph AI Recovery Agent."""
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.llm_client import llm_client
from app.agents.schemas import DiagnosisOutput, StrategyOutput, PromiseExtractionOutput
from app.agents.runner import RecoveryAgentRunner
from app.models import (
    Customer,
    CustomerSegment,
    Transaction,
    TransactionStatus,
    TransactionType,
    RecoveryCase,
    RecoverySourceType,
    RecoveryState,
    AuditLog,
)
from app.db.seed import seed_database


@pytest.mark.asyncio
async def test_llm_client_structured_generation():
    """Test provider-agnostic structured output parsing."""
    diag = await llm_client.generate_structured(
        prompt="Diagnose test failure",
        system_prompt="Test system",
        schema=DiagnosisOutput,
        context={"failure_code": "network_timeout", "amount": 25000.0},
    )
    assert diag.root_cause == "transient_gateway_timeout"
    assert diag.confidence >= 0.80

    strat = await llm_client.generate_structured(
        prompt="Select strategy",
        system_prompt="Test system",
        schema=StrategyOutput,
        context={"failure_code": "card_expired", "amount": 5000.0},
    )
    assert strat.recommended_action is not None
    assert "WHATSAPP" in strat.recommended_channel or "EMAIL" in strat.recommended_channel


@pytest.mark.asyncio
async def test_langgraph_agent_execution_workflow(db_session: AsyncSession):
    """Test full LangGraph workflow execution on a detected recovery case."""
    # Seed db
    await seed_database(db_session)

    # Fetch seeded case RCV-ZS-1002 (Subscription Dunning ₹24,500)
    stmt = select(RecoveryCase).where(RecoveryCase.id == "RCV-ZS-1002")
    res = await db_session.execute(stmt)
    case = res.scalars().first()
    assert case is not None

    # Run LangGraph Agent
    result_state = await RecoveryAgentRunner.process_case(db_session, case.id)
    assert result_state is not None
    assert result_state["diagnosis"]["root_cause"] is not None
    assert result_state["policy_evaluation"]["allowed"] is True

    # Verify updated DB state
    await db_session.refresh(case)
    assert case.ai_reasoning is not None
    assert case.status in [RecoveryState.AWAITING_RESULT, RecoveryState.RECOVERED, RecoveryState.EXECUTING]

    # Verify audit logs were written
    stmt_audit = select(AuditLog).where(AuditLog.case_id == case.id)
    res_audit = await db_session.execute(stmt_audit)
    logs = res_audit.scalars().all()
    assert len(logs) >= 2


@pytest.mark.asyncio
async def test_langgraph_agent_high_value_escalation(db_session: AsyncSession):
    """Test that ₹1.25L case properly triggers human approval escalation."""
    await seed_database(db_session)

    # Case RCV-NX-1001 is ₹1,25,000
    stmt = select(RecoveryCase).where(RecoveryCase.id == "RCV-NX-1001")
    res = await db_session.execute(stmt)
    case = res.scalars().first()
    assert case is not None

    result_state = await RecoveryAgentRunner.process_case(db_session, case.id)
    assert result_state["policy_evaluation"]["requires_human_approval"] is True
    assert result_state["final_status"] == RecoveryState.ESCALATED.value

    await db_session.refresh(case)
    assert case.status == RecoveryState.ESCALATED
