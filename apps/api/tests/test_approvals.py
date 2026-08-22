"""Unit and API tests for Human-in-the-loop Approvals."""
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.seed import seed_database
from app.models import RecoveryCase, RecoveryState, AuditLog, ActorType


@pytest.mark.asyncio
async def test_pending_approvals_listing(client: AsyncClient, db_session: AsyncSession):
    """Test listing cases awaiting human sign-off."""
    await seed_database(db_session)

    res = await client.get("/api/v1/approvals")
    assert res.status_code == 200
    data = res.json()
    assert data["count"] >= 1
    assert any(c["case_id"] == "RCV-NX-1001" for c in data["pending_approvals"])


@pytest.mark.asyncio
async def test_approve_decision_recovers_revenue(client: AsyncClient, db_session: AsyncSession):
    """Test operator approval captures funds and updates recovery case."""
    await seed_database(db_session)

    res = await client.post(
        "/api/v1/approvals/RCV-NX-1001/decision",
        json={
            "decision": "APPROVE",
            "operator_id": "operator_risk_lead",
            "reason": "Verified corporate KYC and bank balance sweep resolved.",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["decision"] == "APPROVE"
    assert data["status"] == RecoveryState.RECOVERED.value
    assert data["recovered_amount"] == 125000.0

    # Verify Audit Log
    stmt_audit = select(AuditLog).where(
        AuditLog.case_id == "RCV-NX-1001",
        AuditLog.actor_type == ActorType.HUMAN_OPERATOR,
    )
    res_audit = await db_session.execute(stmt_audit)
    audit = res_audit.scalars().first()
    assert audit is not None
    assert audit.actor_id == "operator_risk_lead"


@pytest.mark.asyncio
async def test_reject_decision_stops_recovery(client: AsyncClient, db_session: AsyncSession):
    """Test operator rejection stops case and records reason."""
    await seed_database(db_session)

    res = await client.post(
        "/api/v1/approvals/RCV-NX-1001/decision",
        json={
            "decision": "REJECT",
            "operator_id": "operator_fraud_team",
            "reason": "Customer requested account suspension.",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["decision"] == "REJECTED"
    assert data["status"] == RecoveryState.STOPPED.value
