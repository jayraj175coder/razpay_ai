"""Unit and API tests for Promise-to-Pay extraction and tracking."""
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.seed import seed_database
from app.models import PromiseToPay, PromiseStatus, RecoveryCase, RecoveryState


@pytest.mark.asyncio
async def test_promise_extraction_api(client: AsyncClient, db_session: AsyncSession):
    """Test extracting structured promise from natural language customer message."""
    await seed_database(db_session)

    res = await client.post(
        "/api/v1/promises/extract",
        json={
            "case_id": "RCV-NX-1001",
            "customer_id": "cust_enterprise_01",
            "message_text": "We will transfer the entire Rs 125000 on Wednesday afternoon.",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["has_promise"] is True
    assert data["promised_amount"] == 125000.0
    assert data["status"] == "WAITING"


@pytest.mark.asyncio
async def test_promises_list_api(client: AsyncClient, db_session: AsyncSession):
    """Test listing customer promises."""
    await seed_database(db_session)

    res = await client.get("/api/v1/promises")
    assert res.status_code == 200
    data = res.json()
    assert data["count"] >= 1
    assert data["promises"][0]["promised_amount"] > 0


@pytest.mark.asyncio
async def test_promise_fulfillment_reconciles_case(client: AsyncClient, db_session: AsyncSession):
    """Test fulfilling promise updates case to RECOVERED and sets recovered amount."""
    await seed_database(db_session)

    # Fetch seeded promise for RCV-KV-1003
    stmt = select(PromiseToPay).where(PromiseToPay.recovery_case_id == "RCV-KV-1003")
    res = await db_session.execute(stmt)
    prom = res.scalars().first()
    assert prom is not None

    res_fulfill = await client.post(f"/api/v1/promises/{prom.id}/fulfill")
    assert res_fulfill.status_code == 200
    assert res_fulfill.json()["status"] == "FULFILLED"

    # Verify case updated to RECOVERED
    stmt_case = select(RecoveryCase).where(RecoveryCase.id == "RCV-KV-1003")
    res_case = await db_session.execute(stmt_case)
    case = res_case.scalars().first()
    assert case.status == RecoveryState.RECOVERED
    assert case.recovered_amount == 85000.0
