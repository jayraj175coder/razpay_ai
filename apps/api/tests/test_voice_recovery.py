"""Unit and API tests for Hinglish AI Voice Recovery."""
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.seed import seed_database
from app.models import RecoveryCase, RecoveryAction, RecoveryActionType, PromiseToPay, PromiseStatus, AuditLog
from app.services.voice import VoiceRecoveryService


@pytest.mark.asyncio
async def test_generate_voice_script_hinglish(db_session: AsyncSession):
    """Test generating personalized Hinglish voice recovery script."""
    await seed_database(db_session)

    stmt = select(RecoveryCase).limit(1)
    res = await db_session.execute(stmt)
    case = res.scalars().first()
    assert case is not None

    script_data = await VoiceRecoveryService.generate_voice_script(
        session=db_session,
        case_id=case.id,
        language="hinglish",
    )

    assert script_data["case_id"] == case.id
    assert script_data["language"] == "hinglish"
    assert "Namaste" in script_data["script_hinglish"] or "₹" in script_data["script_hinglish"]
    assert len(script_data["script_english"]) > 0
    assert script_data["estimated_duration_seconds"] > 0


@pytest.mark.asyncio
async def test_simulate_voice_call_with_promise_extraction(db_session: AsyncSession):
    """Test executing interactive voice call and capturing customer verbal promise."""
    await seed_database(db_session)

    stmt = select(RecoveryCase).where(RecoveryCase.amount_at_risk == 24500.0)
    res = await db_session.execute(stmt)
    case = res.scalars().first()
    if not case:
        stmt = select(RecoveryCase).limit(1)
        res = await db_session.execute(stmt)
        case = res.scalars().first()

    customer_verbal_response = "Haan main parson subah ₹24,500 clear kar dunga pakka."

    call_result = await VoiceRecoveryService.simulate_voice_call(
        session=db_session,
        case_id=case.id,
        customer_response_text=customer_verbal_response,
    )

    assert call_result["success"] is True
    assert call_result["call_status"] == "COMPLETED"
    assert "payment_link" in call_result
    assert call_result["payment_link"]["short_url"].startswith("http")

    # Verify Promise-to-Pay was automatically recorded from voice
    assert call_result["promise"] is not None
    assert call_result["promise"]["has_promise"] is True
    assert call_result["promise"]["promised_amount"] == 24500.0

    # Verify Action recorded in DB
    stmt_act = select(RecoveryAction).where(RecoveryAction.recovery_case_id == case.id).order_by(RecoveryAction.created_at.desc())
    res_act = await db_session.execute(stmt_act)
    action = res_act.scalars().first()
    assert action is not None
    assert action.action_type == RecoveryActionType.TRIGGER_HINGLISH_VOICE_CALL


@pytest.mark.asyncio
async def test_voice_api_endpoints(client: AsyncClient, db_session: AsyncSession):
    """Test POST /api/v1/voice/generate-script and POST /api/v1/voice/call."""
    await seed_database(db_session)

    stmt = select(RecoveryCase).limit(1)
    res = await db_session.execute(stmt)
    case = res.scalars().first()

    # 1. Test script generation endpoint
    res_script = await client.post(
        "/api/v1/voice/generate-script",
        json={"case_id": case.id, "language": "hinglish"},
    )
    assert res_script.status_code == 200
    data_script = res_script.json()
    assert "script_hinglish" in data_script
    assert data_script["case_id"] == case.id

    # 2. Test call simulation endpoint
    res_call = await client.post(
        "/api/v1/voice/call",
        json={
            "case_id": case.id,
            "customer_response_text": "Will pay the full 125000 invoice tomorrow by 4pm.",
        },
    )
    assert res_call.status_code == 200
    data_call = res_call.json()
    assert data_call["call_status"] == "COMPLETED"
    assert "payment_link" in data_call
    assert data_call["promise"]["has_promise"] is True
