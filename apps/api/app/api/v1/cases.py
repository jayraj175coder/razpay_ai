"""Recovery Cases API Endpoints."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models import RecoveryCase, RecoveryState, ActorType
from app.services.ledger import LedgerService
from app.agents.runner import RecoveryAgentRunner
from app.state_machine.machine import RecoveryStateMachine
from app.providers.factory import get_payment_provider

router = APIRouter()


@router.get("", status_code=status.HTTP_200_OK)
async def list_cases(
    status: Optional[str] = Query(None),
    source_type: Optional[str] = Query(None),
    risk_category: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """List recovery cases with optional filtering."""
    cases = await LedgerService.list_cases(
        session=db,
        status=status,
        source_type=source_type,
        risk_category=risk_category,
        search=search,
        limit=limit,
        offset=offset,
    )
    return {"cases": cases, "count": len(cases)}


@router.get("/{case_id}", status_code=status.HTTP_200_OK)
async def get_case(
    case_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get full case details including customer, attempts, and audit logs."""
    case = await LedgerService.get_case_detail(db, case_id)
    if not case:
        raise HTTPException(status_code=404, detail=f"Case '{case_id}' not found")
    return case


@router.post("/{case_id}/diagnose", status_code=status.HTTP_200_OK)
async def run_ai_diagnosis(
    case_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Trigger LangGraph AI Recovery Agent diagnosis and strategy execution."""
    stmt = select(RecoveryCase).where(RecoveryCase.id == case_id)
    res = await db.execute(stmt)
    case = res.scalars().first()
    if not case:
        raise HTTPException(status_code=404, detail=f"Case '{case_id}' not found")

    result = await RecoveryAgentRunner.process_case(db, case_id)
    updated_case = await LedgerService.get_case_detail(db, case_id)
    return {
        "success": True,
        "state": result,
        "case": updated_case,
    }


@router.post("/{case_id}/approve", status_code=status.HTTP_200_OK)
async def approve_case(
    case_id: str,
    reason: Optional[str] = "Approved by operator via Command Center",
    db: AsyncSession = Depends(get_db),
):
    """Human approval for escalated recovery cases."""
    stmt = select(RecoveryCase).where(RecoveryCase.id == case_id)
    res = await db.execute(stmt)
    case = res.scalars().first()
    if not case:
        raise HTTPException(status_code=404, detail=f"Case '{case_id}' not found")

    if case.status != RecoveryState.ESCALATED and case.status != RecoveryState.POLICY_CHECK:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot approve case in status '{case.status.value}'. Must be in ESCALATED or POLICY_CHECK."
        )

    # Transition to APPROVED
    audit = RecoveryStateMachine.transition(
        case=case,
        to_state=RecoveryState.APPROVED,
        actor_type=ActorType.HUMAN_OPERATOR,
        actor_id="operator_current",
        reason=reason,
    )
    db.add(audit)

    # Execute retry through payment gateway provider
    provider = get_payment_provider()
    retry_res = await provider.retry_payment(
        transaction_id=case.source_id,
        amount=case.amount_at_risk,
        currency=case.currency,
        force_outcome="SUCCESS",
    )

    if retry_res.success:
        case.recovered_amount = case.amount_at_risk
        audit_rec = RecoveryStateMachine.transition(
            case=case,
            to_state=RecoveryState.RECOVERED,
            actor_type=ActorType.RECOVERY_EXECUTOR,
            actor_id="sandbox_provider",
            reason=f"Payment recovered successfully: ₹{case.amount_at_risk:,.0f}",
        )
        db.add(audit_rec)

    await db.commit()

    return {"success": True, "status": case.status.value, "recovered_amount": case.recovered_amount}


@router.post("/{case_id}/reject", status_code=status.HTTP_200_OK)
async def reject_case(
    case_id: str,
    reason: Optional[str] = "Rejected by operator",
    db: AsyncSession = Depends(get_db),
):
    """Human rejection for escalated recovery case."""
    stmt = select(RecoveryCase).where(RecoveryCase.id == case_id)
    res = await db.execute(stmt)
    case = res.scalars().first()
    if not case:
        raise HTTPException(status_code=404, detail=f"Case '{case_id}' not found")

    audit = RecoveryStateMachine.transition(
        case=case,
        to_state=RecoveryState.STOPPED,
        actor_type=ActorType.HUMAN_OPERATOR,
        actor_id="operator_current",
        reason=reason,
    )
    db.add(audit)
    await db.commit()

    return {"success": True, "status": case.status.value, "stopping_reason": case.stopping_reason}
