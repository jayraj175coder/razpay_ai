"""Human Approvals API Router."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.approvals import ApprovalService

router = APIRouter()


class ApprovalDecisionRequest(BaseModel):
    decision: str = Field(..., description="APPROVE, REJECT, or MODIFY")
    operator_id: str = Field(default="operator_admin")
    reason: Optional[str] = Field(None, description="Operator reason or notes")
    modified_amount: Optional[float] = Field(None, description="Override amount if modifying")
    modified_action: Optional[str] = Field(None, description="Override action type if modifying")


@router.get("", status_code=status.HTTP_200_OK)
async def list_pending_approvals(db: AsyncSession = Depends(get_db)):
    """List recovery cases currently awaiting human approval."""
    cases = await ApprovalService.list_pending_approvals(session=db)
    return {"pending_approvals": cases, "count": len(cases)}


@router.post("/{case_id}/decision", status_code=status.HTTP_200_OK)
async def process_approval_decision(
    case_id: str,
    req: ApprovalDecisionRequest,
    db: AsyncSession = Depends(get_db),
):
    """Submit human operator approval, rejection, or modification."""
    try:
        return await ApprovalService.process_decision(
            session=db,
            case_id=case_id,
            decision=req.decision,
            operator_id=req.operator_id,
            reason=req.reason,
            modified_amount=req.modified_amount,
            modified_action=req.modified_action,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
