"""Deterministic Revenue Risk and Recovery Scoring Engine."""
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from app.models.enums import CustomerSegment, RecoverySourceType, RiskCategory


@dataclass
class RiskAssessmentResult:
    amount_at_risk: float
    recovery_probability: float
    priority_score: float
    risk_category: RiskCategory
    positive_signals: List[str] = field(default_factory=list)
    negative_signals: List[str] = field(default_factory=list)
    heuristic_notes: str = ""

    def to_dict(self) -> dict:
        return {
            "amount_at_risk": self.amount_at_risk,
            "recovery_probability": round(self.recovery_probability, 3),
            "priority_score": round(self.priority_score, 1),
            "risk_category": self.risk_category.value,
            "positive_signals": self.positive_signals,
            "negative_signals": self.negative_signals,
            "heuristic_notes": self.heuristic_notes,
        }


# Base baseline probabilities by failure taxonomy
FAILURE_CODE_BASE_PROBABILITY: Dict[str, float] = {
    # Infrastructure & Network (0.85+)
    # NPCI central switch downtime during recurring cycle — pure infra failure, highly recoverable once switch stabilizes
    "npci_downtime": 0.90,
    "network_timeout": 0.88,
    "gateway_error": 0.86,
    "system_busy": 0.85,
    # Issuing bank core banking system downtime — bank-side outage, highly recoverable after cooldown
    "bank_server_error": 0.82,

    # Authentication & User Flow (0.70 - 0.80)
    "auth_failed": 0.78,
    "otp_timeout": 0.76,
    "checkout_abandoned": 0.72,

    # Behavioral & Liquidity (0.50 - 0.70)
    "insufficient_funds": 0.68,
    # Scheduled mandate execution hit low balance — recoverable when resequenced after payroll / balance credit
    "low_balance_recurring": 0.60,
    "card_expired": 0.58,
    # Amount exceeds pre-authorized mandate limit — recoverable if amount is adjusted or split
    "mandate_amount_exceeded": 0.55,
    "mandate_inactive": 0.50,

    # Permanent & Blocked (< 0.20)
    "invalid_card": 0.18,
    # Mandate validity period lapsed — auto-retries will fail; requires explicit customer renewal / re-authorization
    "mandate_expired": 0.15,
    "account_closed": 0.10,
    # Customer cancelled standing instruction with issuer bank — permanently unrecoverable via retry, do not retry
    "mandate_revoked": 0.05,
    "fraud_suspected": 0.05,
    "stolen_card": 0.03,
}


class RevenueRiskEngine:
    """
    Evaluates revenue-at-risk, recovery probability, and composite priority score
    using explainable deterministic scoring heuristics.
    """

    @classmethod
    def assess_risk(
        cls,
        amount: float,
        failure_code: Optional[str] = None,
        source_type: RecoverySourceType = RecoverySourceType.PAYMENT_FAILURE,
        customer_segment: CustomerSegment = CustomerSegment.RETAIL,
        lifetime_value: float = 0.0,
        past_successful_payments: int = 0,
        failed_attempts_count: int = 1,
        invoice_age_days: int = 0,
        has_promise_to_pay: bool = False,
    ) -> RiskAssessmentResult:
        positive_signals: List[str] = []
        negative_signals: List[str] = []

        code = (failure_code or "").lower().strip()
        base_prob = FAILURE_CODE_BASE_PROBABILITY.get(code, 0.65)

        # Signal: Failure code baseline
        if base_prob >= 0.80:
            positive_signals.append(f"Transient error code '{code}' indicates infrastructure/network issue, not delinquency")
        elif base_prob <= 0.20:
            negative_signals.append(f"Severe failure code '{code}' indicates permanent account/security blockage")
        else:
            positive_signals.append(f"Standard recoverable failure type '{code or 'unspecified'}'")

        prob = base_prob

        # 1. Past payment history signals
        if past_successful_payments >= 10:
            prob += 0.12
            positive_signals.append(f"+ High transaction track record: {past_successful_payments} successful past settlements")
        elif past_successful_payments >= 3:
            prob += 0.06
            positive_signals.append(f"+ Positive payment history: {past_successful_payments} successful past payments")
        elif past_successful_payments == 0:
            prob -= 0.05
            negative_signals.append("- First-time transaction with no prior payment history")

        # 2. Customer Lifetime Value (LTV)
        if lifetime_value >= 1000000.0:  # >= ₹10 Lakhs
            prob += 0.08
            positive_signals.append(f"+ High LTV Enterprise Account (₹{lifetime_value:,.0f} historical value)")
        elif lifetime_value >= 100000.0:  # >= ₹1 Lakh
            prob += 0.04
            positive_signals.append(f"+ Established customer LTV (₹{lifetime_value:,.0f})")

        # 3. Customer Segment
        seg_val = customer_segment.value if hasattr(customer_segment, "value") else str(customer_segment)
        if seg_val in ["ENTERPRISE", "VIP"]:
            prob += 0.05
            positive_signals.append(f"+ Prioritized customer tier: {seg_val}")

        # 4. Promise to Pay
        if has_promise_to_pay:
            prob += 0.15
            positive_signals.append("+ Active Promise-to-Pay confirmed by customer")

        # 5. Penalties: Repeated Failed Attempts
        if failed_attempts_count > 1:
            penalty = min(0.12 * (failed_attempts_count - 1), 0.30)
            prob -= penalty
            negative_signals.append(f"- Repeated failure: {failed_attempts_count} unsuccessful recovery attempts so far")

        # 6. Penalties: Invoice Age
        if invoice_age_days > 60:
            prob -= 0.25
            negative_signals.append(f"- Highly aged receivable: {invoice_age_days} days overdue")
        elif invoice_age_days > 30:
            prob -= 0.12
            negative_signals.append(f"- Overdue invoice age: {invoice_age_days} days overdue")
        elif invoice_age_days > 7:
            prob -= 0.05
            negative_signals.append(f"- Mild overdue age: {invoice_age_days} days overdue")

        # Clamp probability between 0.05 and 0.98
        final_probability = max(0.05, min(0.98, prob))

        # Priority Score Calculation (0 - 100)
        # Weights: Amount Impact (40%), Probability (35%), LTV (15%), Urgency (10%)
        # Normalize amount up to ₹2,00,000 as 100%
        amount_norm = min(amount / 200000.0, 1.0) * 40.0
        prob_norm = final_probability * 35.0
        ltv_norm = min(lifetime_value / 1000000.0, 1.0) * 15.0
        urgency_norm = (10.0 if failed_attempts_count <= 2 else 5.0)

        priority_score = min(100.0, max(1.0, amount_norm + prob_norm + ltv_norm + urgency_norm))

        # Assign Risk Category
        if amount >= 100000.0 or priority_score >= 85.0:
            risk_category = RiskCategory.CRITICAL
        elif amount >= 25000.0 or priority_score >= 70.0:
            risk_category = RiskCategory.HIGH
        elif priority_score >= 40.0:
            risk_category = RiskCategory.MEDIUM
        else:
            risk_category = RiskCategory.LOW

        heuristic_notes = (
            f"Heuristic score derived from {len(positive_signals)} positive signals and "
            f"{len(negative_signals)} risk factors."
        )

        return RiskAssessmentResult(
            amount_at_risk=amount,
            recovery_probability=final_probability,
            priority_score=priority_score,
            risk_category=risk_category,
            positive_signals=positive_signals,
            negative_signals=negative_signals,
            heuristic_notes=heuristic_notes,
        )
