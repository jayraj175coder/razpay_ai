"""Health check endpoint."""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db

router = APIRouter()


@router.get("", status_code=status.HTTP_200_OK)
async def get_health(db: AsyncSession = Depends(get_db)):
    """Check service health and database connectivity."""
    db_status = "healthy"
    try:
        await db.execute(text("SELECT 1"))
    except Exception as exc:
        db_status = f"unhealthy: {str(exc)}"

    return {
        "status": "healthy" if db_status == "healthy" else "degraded",
        "app_name": settings.APP_NAME,
        "environment": settings.ENVIRONMENT,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "database": db_status,
        "llm_provider": settings.LLM_PROVIDER,
        "payment_provider": settings.PAYMENT_PROVIDER,
        "version": "1.0.0",
    }
