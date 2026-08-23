import json
from typing import Optional
import uuid
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.logging import get_logger
from app.providers.razorpay_provider import RazorpayProvider
from app.webhooks.processor import WebhookProcessor

logger = get_logger("recoverai.api.webhooks")
router = APIRouter()


@router.post("/razorpay", status_code=status.HTTP_200_OK)
async def handle_razorpay_webhook(
    request: Request,
    x_razorpay_signature: Optional[str] = Header(None),
    x_razorpay_event_id: Optional[str] = Header(None),
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

    # Enforce signature verification when in Razorpay mode or when signature is supplied with secret configured
    if settings.PAYMENT_PROVIDER == "razorpay" or (
        x_razorpay_signature and settings.RAZORPAY_WEBHOOK_SECRET and "placeholder" not in settings.RAZORPAY_WEBHOOK_SECRET
    ):
        if not x_razorpay_signature or not RazorpayProvider.verify_webhook_signature(raw_body, x_razorpay_signature):
            logger.warning("Rejected webhook due to invalid Razorpay signature")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid Razorpay webhook signature",
            )

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
