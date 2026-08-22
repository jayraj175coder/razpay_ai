# LangGraph Agent Design & Structured Reasoning

RecoverAI uses an autonomous 10-node **LangGraph** orchestration graph that processes every detected revenue leakage event with structured Pydantic schemas.

---

## 1. 10-Node Workflow Topology

```
 [1. load_case]
       │
       ▼
 [2. load_customer_context]
       │
       ▼
 [3. diagnose] (LLM Root Cause Analysis)
       │
       ▼
 [4. calculate_recovery_score] (Deterministic Risk Math)
       │
       ▼
 [5. select_strategy] (LLM Context-Aware Strategy Synthesis)
       │
       ▼
 [6. policy_check] (Deterministic Bounded Policy Engine Gate)
       │
       ▼
 [7. execute_or_escalate] (Branch: Auto-execute or Human Queue)
       │
       ▼
 [8. verify_result] (Gateway Verification & Settlement Check)
       │
       ▼
 [9. update_recovery_ledger] (Financial Ledger Reconciliation)
       │
       ▼
 [10. write_audit_log] (Immutable Trace Recording)
```

---

## 2. Structured Pydantic Schemas

### Diagnosis Schema (`DiagnosisOutput`)
```python
class DiagnosisOutput(BaseModel):
    root_cause: str = Field(description="Primary diagnosed technical or customer root cause")
    root_cause_category: str = Field(description="TECHNICAL, CUSTOMER, FRAUD, or INVOICE")
    explanation: str = Field(description="2-3 sentence financial explanation")
    confidence: float = Field(ge=0.0, le=1.0)
    positive_signals: List[str]
    negative_signals: List[str]
```

### Strategy Schema (`StrategyOutput`)
```python
class StrategyOutput(BaseModel):
    recommended_action: str = Field(description="SMART_RETRY, PAYMENT_LINK, DISCOUNT_OFFER, HUMAN_ESCALATION, or STOP")
    channel: str = Field(description="SMART_RETRY, WHATSAPP, EMAIL, SMS, or OPERATOR_CALL")
    suggested_delay_hours: int
    discount_pct: float
    message_draft: Optional[str]
    rationale: str
```

### Promise Extraction Schema (`PromiseExtractionOutput`)
```python
class PromiseExtractionOutput(BaseModel):
    has_promise: bool
    promised_amount: Optional[float]
    promised_date: Optional[str]
    confidence: float = Field(ge=0.0, le=1.0)
    notes: Optional[str]
```

---

## 3. Provider-Agnostic LLM Client & Resilient Fallbacks

The `LLMClient` supports:
- **Google Gemini API** (`gemini-1.5-flash`, `gemini-1.5-pro` via `google-genai` / `google.generativeai`)
- **OpenAI API** (`gpt-4o`, `gpt-4o-mini`)
- **Anthropic API** (`claude-3-5-sonnet`)
- **Deterministic Mock Engine**: Evaluates contextual heuristics and returns validated Pydantic outputs with zero network latency, ensuring offline operability and predictable test suites.
