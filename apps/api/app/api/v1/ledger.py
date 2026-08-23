"""Financial Ledger and Audit Trail Endpoints."""
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models import AuditLog, ActorType
from app.services.ledger import LedgerService

router = APIRouter()


@router.get("/metrics", status_code=status.HTTP_200_OK)
async def get_metrics(db: AsyncSession = Depends(get_db)):
    """Retrieve aggregate financial metrics and recovery statistics from database ledger."""
    return await LedgerService.get_metrics(db)


@router.get("/audit", status_code=status.HTTP_200_OK)
async def get_audit_trail(
    case_id: Optional[str] = Query(None),
    actor_type: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Query immutable audit log history."""
    query = select(AuditLog).order_by(desc(AuditLog.created_at))

    if case_id:
        query = query.where(AuditLog.case_id == case_id)
    if actor_type:
        query = query.where(AuditLog.actor_type == ActorType(actor_type))

    query = query.limit(limit).offset(offset)
    res = await db.execute(query)
    logs = res.scalars().all()

    return {
        "audit_logs": [
            {
                "id": log.id,
                "case_id": log.case_id,
                "actor_type": log.actor_type.value,
                "actor_id": log.actor_id,
                "action": log.action,
                "reason": log.reason,
                "metadata": log.metadata_json,
                "prev_hash": log.prev_hash,
                "entry_hash": log.entry_hash,
                "created_at": log.created_at.isoformat(),
            }
            for log in logs
        ],
        "count": len(logs),
    }
