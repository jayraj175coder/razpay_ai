"""Hinglish AI Voice Recovery API Router."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.voice import VoiceRecoveryService

router = APIRouter()


class VoiceScriptRequest(BaseModel):
    case_id: str = Field(..., description="Target recovery case identifier")
    language: str = Field(default="hinglish", description="Target language dialect: hinglish or english")


class VoiceCallSimulationRequest(BaseModel):
    case_id: str = Field(..., description="Target recovery case identifier")
    customer_response_text: Optional[str] = Field(None, description="Optional verbal customer response to extract promises from")
    operator_id: str = Field(default="ai_voice_agent", description="Voice agent operator ID")


@router.post("/generate-script", status_code=status.HTTP_200_OK)
async def generate_voice_script(
    req: VoiceScriptRequest,
    db: AsyncSession = Depends(get_db),
):
    """Generate tailored conversational Hinglish recovery script for an unpaid transaction."""
    try:
        return await VoiceRecoveryService.generate_voice_script(
            session=db,
            case_id=req.case_id,
            language=req.language,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/call", status_code=status.HTTP_200_OK)
async def simulate_voice_call(
    req: VoiceCallSimulationRequest,
    db: AsyncSession = Depends(get_db),
):
    """Execute an automated outbound AI Hinglish recovery call, parse responses, and dispatch 1-click links."""
    try:
        return await VoiceRecoveryService.simulate_voice_call(
            session=db,
            case_id=req.case_id,
            customer_response_text=req.customer_response_text,
            operator_id=req.operator_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
