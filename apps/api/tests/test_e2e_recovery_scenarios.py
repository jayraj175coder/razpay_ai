"""End-to-End Integration and Failure Scenario Test Suite for RecoverAI."""
import pytest
from httpx import AsyncClient
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import RecoveryCase, RecoveryState, RecoveryAction, AuditLog, WebhookEvent, PromiseToPay, PromiseStatus


@pytest.mark.asyncio
async def test_e2e_flow_1_webhook_to_case_creation(client: AsyncClient, db_session: AsyncSession):
    """Flow 1: Webhook ingestion -> SHA-256 deduplication -> Case creation with risk score."""
    webhook_payload = {
        "event": "payment.failed",
        "payment": {
            "entity": {
                "id": "pay_test_e2e_001",
                "amount": 2500000,  # ₹25,000 in paise
                "currency": "INR",
                "error_code": "network_timeout",
                "error_description": "Issuer switch timeout",
                "email": "cto@zenithcloud.io",
            }
        },
        "customer": {
            "name": "Zenith Cloud Solutions",
            "email": "cto@zenithcloud.io",
            "segment": "VIP",
            "lifetime_value": 450000.0,
        },
    }

    # Step 1: Ingest webhook
    res = await client.post("/api/v1/webhooks/simulate", json=webhook_payload)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["duplicate"] is False
    case_id = data["data"]["case_id"]
    assert case_id is not None

    # Step 2: Query DB to verify Case state and risk calculations
    stmt = select(RecoveryCase).where(RecoveryCase.id == case_id)
    case_res = await db_session.execute(stmt)
    case = case_res.scalars().first()
    assert case is not None
    assert case.amount_at_risk == 25000.0
    assert case.status == RecoveryState.DETECTED
    assert case.recovery_probability > 0.5
    assert case.priority_score > 50


@pytest.mark.asyncio
async def test_e2e_flow_2_webhook_idempotency_duplicate_prevention(client: AsyncClient, db_session: AsyncSession):
    """Flow 2: Webhook duplicate payload is safely deduplicated without creating duplicate cases."""
    webhook_payload = {
        "event_id": "evt_test_idempotent_999",
        "event": "payment.failed",
        "amount": 18000.0,
        "failure_code": "network_timeout",
        "customer": {
            "name": "FastTrack Courier",
            "email": "accounts@fasttrack.in",
            "segment": "SMB",
        },
    }

    # First delivery
    res1 = await client.post("/api/v1/webhooks/simulate", json=webhook_payload)
    assert res1.status_code == 200
    assert res1.json()["duplicate"] is False

    # Immediate duplicate delivery
    res2 = await client.post("/api/v1/webhooks/simulate", json=webhook_payload)
    assert res2.status_code == 200
    assert res2.json()["duplicate"] is True
    assert "Duplicate" in res2.json()["message"]


@pytest.mark.asyncio
async def test_e2e_flow_3_full_automated_recovery_lifecycle(client: AsyncClient, db_session: AsyncSession):
    """Flow 3: Detect -> AI Diagnose & Strategy -> Policy Gate -> Gateway Execution -> RECOVERED."""
    # Ingest transient network timeout
    webhook_payload = {
        "event": "subscription.payment_failed",
        "subscription": {
            "id": "sub_e2e_auto_777",
            "amount": 14999.0,
        },
        "customer": {
            "name": "Acme Media India",
            "email": "billing@acmemedia.in",
            "segment": "SMB",
            "lifetime_value": 180000.0,
        },
    }

    res_wh = await client.post("/api/v1/webhooks/simulate", json=webhook_payload)
    assert res_wh.status_code == 200
    case_id = res_wh.json()["data"]["case_id"]

    # Trigger AI Diagnosis and execution graph
    res_diag = await client.post(f"/api/v1/cases/{case_id}/diagnose")
    assert res_diag.status_code == 200
    diag_data = res_diag.json()
    case_detail = diag_data["case"]

    assert case_detail["id"] == case_id
    assert case_detail["root_cause"] is not None
    assert case_detail["status"] in [RecoveryState.RECOVERED.value, RecoveryState.EXECUTING.value]

    # Verify Audit trail was generated across all nodes
    stmt_audit = select(AuditLog).where(AuditLog.case_id == case_id)
    audit_res = await db_session.execute(stmt_audit)
    audits = audit_res.scalars().all()
    assert len(audits) >= 2
    action_types = [a.action for a in audits]
    assert "AI_DIAGNOSIS_AND_STRATEGY_GENERATED" in action_types or "POLICY_DECISION_RECORDED" in action_types


@pytest.mark.asyncio
async def test_e2e_flow_4_fraud_security_stopping_rule(client: AsyncClient, db_session: AsyncSession):
    """Flow 4: Fraud transaction -> Policy Engine strictly blocks execution -> State STOPPED."""
    webhook_payload = {
        "event": "payment.failed",
        "payment": {
            "entity": {
                "id": "pay_fraud_e2e_666",
                "amount": 850000,
                "currency": "INR",
                "error_code": "fraud_suspected",
                "error_description": "Card blacklisted by security engine",
                "email": "unknown@shadow.net",
            }
        },
        "customer": {
            "name": "Anonymous Buyer",
            "email": "unknown@shadow.net",
            "segment": "RETAIL",
            "lifetime_value": 0.0,
        },
    }

    res_wh = await client.post("/api/v1/webhooks/simulate", json=webhook_payload)
    case_id = res_wh.json()["data"]["case_id"]

    # Run AI Diagnosis
    res_diag = await client.post(f"/api/v1/cases/{case_id}/diagnose")
    assert res_diag.status_code == 200
    diag_data = res_diag.json()
    case_detail = diag_data["case"]

    # Policy gate must strictly halt and STOP
    assert case_detail["status"] == RecoveryState.STOPPED.value
    assert case_detail["recovered_amount"] == 0.0


@pytest.mark.asyncio
async def test_e2e_flow_5_high_value_human_escalation_and_approval(client: AsyncClient, db_session: AsyncSession):
    """Flow 5: High-value B2B invoice (₹1,85,000) -> Policy escalates -> Human approves -> RECOVERED."""
    webhook_payload = {
        "event": "invoice.overdue",
        "invoice": {
            "id": "inv_e2e_highval_888",
            "amount": 185000.0,
            "overdue_days": 15,
        },
        "customer": {
            "name": "Bharat Heavy Infra Ltd",
            "email": "accounts@bharatinfra.in",
            "segment": "ENTERPRISE",
            "lifetime_value": 3200000.0,
        },
    }

    res_wh = await client.post("/api/v1/webhooks/simulate", json=webhook_payload)
    case_id = res_wh.json()["data"]["case_id"]

    # Run AI diagnosis
    res_diag = await client.post(f"/api/v1/cases/{case_id}/diagnose")
    diag_data = res_diag.json()
    case_detail = diag_data["case"]

    # Amount >= ₹1,00,000 -> must escalate to human operator
    assert case_detail["status"] == RecoveryState.ESCALATED.value

    # Human operator reviews and approves
    res_app = await client.post(
        f"/api/v1/approvals/{case_id}/decision",
        json={
            "decision": "APPROVE",
            "operator_id": "operator_b2b_lead",
            "reason": "Confirmed customer approved RTGS settlement",
        },
    )
    assert res_app.status_code == 200
    app_data = res_app.json()
    assert app_data["status"] == RecoveryState.RECOVERED.value
    assert app_data["recovered_amount"] == 185000.0
