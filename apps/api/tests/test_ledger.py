"""Integration tests for Recovery Ledger, Cases API, and Metrics Calculation."""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.seed import seed_database
from app.models import RecoveryCase, RecoveryState


@pytest.mark.asyncio
async def test_ledger_metrics_calculation(client: AsyncClient, db_session: AsyncSession):
    """Test ledger metrics calculation from database rows."""
    await seed_database(db_session)

    response = await client.get("/api/v1/ledger/metrics")
    assert response.status_code == 200
    data = response.json()
    assert data["total_revenue_at_risk"] > 0
    assert data["total_recovered_revenue"] >= 7999.0  # From seeded RCV-RS-1004
    assert data["total_cases_count"] >= 4
    assert "source_breakdown" in data
    assert len(data["source_breakdown"]) > 0


@pytest.mark.asyncio
async def test_cases_listing_and_filtering(client: AsyncClient, db_session: AsyncSession):
    """Test listing and filtering recovery cases."""
    await seed_database(db_session)

    # List all
    res = await client.get("/api/v1/cases")
    assert res.status_code == 200
    data = res.json()
    assert data["count"] >= 4
    assert data["cases"][0]["customer_name"] != ""

    # Filter by source_type
    res_filtered = await client.get("/api/v1/cases?source_type=SUBSCRIPTION_DUNNING")
    assert res_filtered.status_code == 200
    data_filtered = res_filtered.json()
    assert all(c["source_type"] == "SUBSCRIPTION_DUNNING" for c in data_filtered["cases"])


@pytest.mark.asyncio
async def test_case_detail_endpoint(client: AsyncClient, db_session: AsyncSession):
    """Test fetching single case investigation profile."""
    await seed_database(db_session)

    res = await client.get("/api/v1/cases/RCV-NX-1001")
    assert res.status_code == 200
    case = res.json()
    assert case["id"] == "RCV-NX-1001"
    assert case["amount_at_risk"] == 125000.0
    assert case["customer"]["name"] == "Nexus Cloud Technologies Pvt Ltd"
    assert "audit_logs" in case
    assert len(case["audit_logs"]) >= 1


@pytest.mark.asyncio
async def test_case_human_approval_workflow(client: AsyncClient, db_session: AsyncSession):
    """Test human approval endpoint transitions case to RECOVERED and updates recovered amount."""
    await seed_database(db_session)

    # RCV-NX-1001 is in POLICY_CHECK
    res_approve = await client.post(
        "/api/v1/cases/RCV-NX-1001/approve",
        params={"reason": "Approved by senior risk officer"},
    )
    assert res_approve.status_code == 200
    data = res_approve.json()
    assert data["status"] == RecoveryState.RECOVERED.value
    assert data["recovered_amount"] == 125000.0

    # Verify metrics updated
    res_metrics = await client.get("/api/v1/ledger/metrics")
    metrics = res_metrics.json()
    assert metrics["total_recovered_revenue"] >= 132999.0  # 125k + 7999
