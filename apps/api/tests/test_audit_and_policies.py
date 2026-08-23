"""Unit and API tests for Policy Management and Audit Trail."""
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.seed import seed_database
from app.models import RecoveryPolicy, AuditLog, ActorType


@pytest.mark.asyncio
async def test_get_active_policy_endpoint(client: AsyncClient, db_session: AsyncSession):
    """Test retrieving active policy."""
    await seed_database(db_session)

    res = await client.get("/api/v1/policies/active")
    assert res.status_code == 200
    data = res.json()
    assert data["version"] >= 1
    assert data["max_payment_retries"] == 3
    assert data["human_approval_threshold"] == 100000.0


@pytest.mark.asyncio
async def test_create_new_policy_version_and_audit(client: AsyncClient, db_session: AsyncSession):
    """Test creating Policy v2 deactivates v1 and writes audit trail."""
    await seed_database(db_session)

    res = await client.post(
        "/api/v1/policies",
        json={
            "name": "Strict Q3 Recovery Bounds",
            "max_payment_retries": 2,
            "max_messages": 1,
            "communication_window_hours": 120,
            "max_discount_pct": 3.0,
            "human_approval_threshold": 50000.0,
            "retry_delay_hours": 12,
            "escalation_delay_hours": 48,
        },
    )
    assert res.status_code == 201
    data = res.json()
    assert data["version"] >= 2

    # Verify active policy switched to new version
    res_active = await client.get("/api/v1/policies/active")
    active_data = res_active.json()
    assert active_data["version"] == data["version"]
    assert active_data["max_payment_retries"] == 2
    assert active_data["human_approval_threshold"] == 50000.0

    # Verify audit log recorded
    stmt_audit = select(AuditLog).where(AuditLog.action == "POLICY_VERSION_CREATED")
    res_audit = await db_session.execute(stmt_audit)
    audit = res_audit.scalars().first()
    assert audit is not None
    assert audit.actor_type == ActorType.HUMAN_OPERATOR


@pytest.mark.asyncio
async def test_audit_logs_query_api(client: AsyncClient, db_session: AsyncSession):
    """Test querying audit logs with actor filter."""
    await seed_database(db_session)

    res = await client.get("/api/v1/ledger/audit")
    assert res.status_code == 200
    data = res.json()
    assert data["count"] >= 3
    assert all("action" in log and "actor_type" in log for log in data["audit_logs"])
    assert all(log.get("entry_hash") is not None and len(log["entry_hash"]) == 64 for log in data["audit_logs"])
