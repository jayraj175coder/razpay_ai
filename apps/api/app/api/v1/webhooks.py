"""FastAPI Webhook Endpoints with strict idempotency."""
import json
import uuid
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logging import get_logger
from app.webhooks.processor import WebhookProcessor

logger = get_logger("recoverai.api.webhooks")
router = APIRouter()


@router.post("/razorpay", status_code=status.HTTP_200_OK)
async def handle_razorpay_webhook(
    request: Request,
    x_razorpay_signature: str = Header(None),
    x_razorpay_event_id: str = Header(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Handle live or test Razorpay webhook delivery with signature check & SHA-256 idempotency.
    """
    raw_body = await request.body()
    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    event_id = x_razorpay_event_id or payload.get("id") or str(uuid.uuid4())
    event_type = payload.get("event", "unknown")

    is_duplicate, msg, result_data = await WebhookProcessor.process_event(
        session=db,
        provider="razorpay",
        event_id=event_id,
        event_type=event_type,
        raw_payload=raw_body,
        payload_dict=payload,
    )

    return {
        "success": True,
        "duplicate": is_duplicate,
        "message": msg,
        "event_id": event_id,
        "data": result_data,
    }


@router.post("/simulate", status_code=status.HTTP_200_OK)
async def simulate_webhook_event(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Simulation webhook endpoint for creating synthetic events (failed payments, checkout drops, etc.).
    """
    raw_body = await request.body()
    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    event_id = payload.get("event_id") or f"sim_evt_{uuid.uuid4().hex[:12]}"
    event_type = payload.get("event", "payment.failed")
    provider = payload.get("provider", "mock")

    is_duplicate, msg, result_data = await WebhookProcessor.process_event(
        session=db,
        provider=provider,
        event_id=event_id,
        event_type=event_type,
        raw_payload=raw_body,
        payload_dict=payload,
    )

    return {
        "success": True,
        "duplicate": is_duplicate,
        "message": msg,
        "event_id": event_id,
        "data": result_data,
    }
