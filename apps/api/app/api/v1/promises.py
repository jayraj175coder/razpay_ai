"""Promise-to-Pay API Router."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.promises import PromiseService

router = APIRouter()


class PromiseExtractRequest(BaseModel):
    case_id: str
    customer_id: str
    message_text: str


@router.get("", status_code=status.HTTP_200_OK)
async def list_promises(
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """List customer promise-to-pay commitments."""
    promises = await PromiseService.list_promises(session=db, status=status)
    return {"promises": promises, "count": len(promises)}


@router.post("/extract", status_code=status.HTTP_200_OK)
async def extract_promise(
    req: PromiseExtractRequest,
    db: AsyncSession = Depends(get_db),
):
    """Extract and record promise from raw customer text message."""
    result = await PromiseService.extract_and_record(
        session=db,
        case_id=req.case_id,
        customer_id=req.customer_id,
        message_text=req.message_text,
    )
    return result


@router.post("/{promise_id}/fulfill", status_code=status.HTTP_200_OK)
async def fulfill_promise(
    promise_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Mark a promise as fulfilled."""
    try:
        return await PromiseService.fulfill_promise(session=db, promise_id=promise_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/{promise_id}/escalate", status_code=status.HTTP_200_OK)
async def escalate_promise(
    promise_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Escalate a broken promise."""
    try:
        return await PromiseService.escalate_broken_promise(session=db, promise_id=promise_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
