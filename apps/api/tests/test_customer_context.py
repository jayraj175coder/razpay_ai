"""Unit tests for CustomerContextService."""
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.seed import seed_database
from app.models import Customer
from app.services.customer_context import CustomerContextService


@pytest.mark.asyncio
async def test_customer_context_aggregation(db_session: AsyncSession):
    """Test CustomerContextService accurately queries and aggregates customer database history."""
    await seed_database(db_session)

    # 1. Test Enterprise customer c1 (Nexus Cloud)
    stmt = select(Customer).where(Customer.email == "finance@nexuscloud.in")
    res = await db_session.execute(stmt)
    c1 = res.scalars().first()
    assert c1 is not None

    ctx = await CustomerContextService.load_customer_context(db_session, c1.id)
    assert ctx.customer_id == c1.id
    assert ctx.name == "Nexus Cloud Technologies Pvt Ltd"
    assert ctx.lifetime_value == 1450000.0
    assert ctx.successful_payments_count >= 1
    assert ctx.overdue_invoices_count >= 1
    assert ctx.total_overdue_invoice_amount == 125000.0


@pytest.mark.asyncio
async def test_customer_context_nonexistent_fallback(db_session: AsyncSession):
    """Test CustomerContextService returns safe fallback for unknown customer."""
    ctx = await CustomerContextService.load_customer_context(db_session, "nonexistent-id-999")
    assert ctx.customer_id == "nonexistent-id-999"
    assert ctx.name == "Unknown Customer"
    assert ctx.lifetime_value == 0.0
    assert ctx.successful_payments_count == 0
