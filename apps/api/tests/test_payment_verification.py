"""Unit tests for PaymentVerificationService."""
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.seed import seed_database
from app.models import RecoveryCase, RecoveryState, PaymentStatus, RecoveryAttempt
from app.providers.mock_provider import MockPaymentProvider
from app.services.payment_verification import PaymentVerificationService


@pytest.mark.asyncio
async def test_payment_verification_service_captured(db_session: AsyncSession):
    """Test successful verification updates case to RECOVERED and creates attempt."""
    await seed_database(db_session)

    stmt = select(RecoveryCase).where(RecoveryCase.id == "RCV-KV-1003")
    res = await db_session.execute(stmt)
    case = res.scalars().first()
    assert case is not None

    provider = MockPaymentProvider()
    retry_res = await provider.retry_payment(
        transaction_id=case.source_id,
        amount=85000.0,
        force_outcome="SUCCESS",
    )

    is_verified, v_result = await PaymentVerificationService.verify_and_reconcile(
        session=db_session,
        case=case,
        provider_reference=retry_res.provider_reference,
        attempted_amount=85000.0,
        provider=provider,
    )

    assert is_verified is True
    assert v_result.is_verified_captured is True
    assert case.status == RecoveryState.RECOVERED
    assert case.recovered_amount == 85000.0

    # Verify attempt record in DB
    stmt_att = select(RecoveryAttempt).where(RecoveryAttempt.recovery_case_id == case.id)
    att_res = await db_session.execute(stmt_att)
    attempts = att_res.scalars().all()
    assert any(a.details_json and a.details_json.get("provider_reference") == retry_res.provider_reference for a in attempts)


@pytest.mark.asyncio
async def test_payment_verification_service_failed_attempts(db_session: AsyncSession):
    """Test failed verification schedules retry or fails without marking RECOVERED."""
    await seed_database(db_session)

    stmt = select(RecoveryCase).where(RecoveryCase.id == "RCV-ZS-1002")
    res = await db_session.execute(stmt)
    case = res.scalars().first()
    assert case is not None

    provider = MockPaymentProvider()
    retry_res = await provider.retry_payment(
        transaction_id=case.source_id,
        amount=14999.0,
        force_outcome="FAILED",
    )

    is_verified, v_result = await PaymentVerificationService.verify_and_reconcile(
        session=db_session,
        case=case,
        provider_reference=retry_res.provider_reference,
        attempted_amount=14999.0,
        provider=provider,
    )

    assert is_verified is False
    assert v_result.is_verified_captured is False
    assert case.status in [RecoveryState.RETRY_SCHEDULED, RecoveryState.FAILED]
    assert case.recovered_amount == 0.0
