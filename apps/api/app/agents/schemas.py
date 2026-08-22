"""Structured Pydantic schemas for AI agent reasoning and tool interfaces."""
from typing import List, Optional
from pydantic import BaseModel, Field
from app.models.enums import RecoveryActionType, RiskCategory


class DiagnosisOutput(BaseModel):
    """Structured root-cause diagnosis output from LLM."""
    root_cause: str = Field(..., description="Machine-readable root cause key e.g. temporary_insufficient_funds, card_expired, network_timeout")
    explanation: str = Field(..., description="Human-readable explanation of why the payment failed based on customer and transaction context")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score between 0.0 and 1.0")
    risk_category: RiskCategory = Field(default=RiskCategory.MEDIUM, description="Assessed risk level")


class StrategyOutput(BaseModel):
    """Structured recovery intervention strategy output from LLM."""
    recommended_action: RecoveryActionType = Field(..., description="Proposed safe recovery action")
    recommended_channel: str = Field(default="EMAIL", description="Communication or execution channel: SMART_RETRY, EMAIL, WHATSAPP, PHONE_ESCALATION, PAYMENT_LINK")
    reasoning: str = Field(..., description="Contextual rationale for why this strategy is optimal and safe")
    customer_message: Optional[str] = Field(None, description="Personalized non-intrusive reminder or recovery copy tailored for Indian business/consumer context")
    proposed_discount_pct: float = Field(default=0.0, ge=0.0, le=50.0, description="Proposed discount % if checkout dropoff recovery")
    retry_delay_hours: int = Field(default=24, ge=1, le=168, description="Optimal delay before executing retry")


class PromiseExtractionOutput(BaseModel):
    """Structured promise to pay extracted from natural language text."""
    has_promise: bool = Field(..., description="True if customer explicitly promised payment")
    promised_amount: Optional[float] = Field(None, description="Extracted numerical promise amount in INR")
    promised_date: Optional[str] = Field(None, description="Extracted promise date in ISO format YYYY-MM-DD")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Extraction confidence score")
    notes: Optional[str] = Field(None, description="Key condition or note mentioned by customer")
