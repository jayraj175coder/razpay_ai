"""Deterministic Bounded Policy Engine for Recovery Actions."""
from dataclasses import dataclass, field
from typing import List, Optional
from app.models.enums import PolicyDecision, RecoveryActionType
from app.models.recovery_policy import RecoveryPolicy


@dataclass
class PolicyEvaluationResult:
    allowed: bool
    decision: PolicyDecision
    reason: str
    policy_version: int
    requires_human_approval: bool
    violated_rules: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "allowed": self.allowed,
            "decision": self.decision.value,
            "reason": self.reason,
            "policy_version": self.policy_version,
            "requires_human_approval": self.requires_human_approval,
            "violated_rules": self.violated_rules,
        }


# Security failure codes that MUST never be automatically retried
DEFAULT_DISALLOWED_FAILURE_CODES = {
    "fraud_suspected",
    "stolen_card",
    "account_frozen",
    "card_lost",
    "sanction_block",
}


class PolicyEngine:
    """
    Deterministic rule engine that validates proposed AI actions against
    enforceable financial policies, safety limits, and human approval gates.
    """

    @classmethod
    def evaluate(
        cls,
        policy: RecoveryPolicy,
        action_type: RecoveryActionType,
        amount_at_risk: float,
        failure_code: Optional[str] = None,
        attempts_count: int = 0,
        messages_sent: int = 0,
        proposed_discount_pct: float = 0.0,
    ) -> PolicyEvaluationResult:
        violated_rules: List[str] = []
        code = (failure_code or "").lower().strip()

        # Rule 1: Fraud / Security Blocklist
        disallowed_codes = set(
            (policy.rules_json or {}).get("disallowed_failure_codes", DEFAULT_DISALLOWED_FAILURE_CODES)
        )
        if code in disallowed_codes:
            violated_rules.append(f"Security policy prohibits automated actions for failure code '{code}'")
            return PolicyEvaluationResult(
                allowed=False,
                decision=PolicyDecision.BLOCKED,
                reason=f"Action prohibited: Security blocklist triggered for '{code}'.",
                policy_version=policy.version,
                requires_human_approval=False,
                violated_rules=violated_rules,
            )

        # Rule 2: Max Payment Retries Boundary
        if action_type == RecoveryActionType.RETRY_PAYMENT:
            if attempts_count >= policy.max_payment_retries:
                violated_rules.append(
                    f"Retry limit exceeded: {attempts_count} attempts made >= max allowed {policy.max_payment_retries}"
                )
                return PolicyEvaluationResult(
                    allowed=False,
                    decision=PolicyDecision.BLOCKED,
                    reason=f"Action blocked: Maximum retries limit ({policy.max_payment_retries}) reached.",
                    policy_version=policy.version,
                    requires_human_approval=False,
                    violated_rules=violated_rules,
                )

        # Rule 3: Communication Frequency Limit
        if action_type in [
            RecoveryActionType.SEND_PAYMENT_REMINDER,
            RecoveryActionType.CREATE_PAYMENT_LINK,
        ]:
            if messages_sent >= policy.max_messages:
                violated_rules.append(
                    f"Communication limit exceeded: {messages_sent} messages sent >= max allowed {policy.max_messages}"
                )
                return PolicyEvaluationResult(
                    allowed=False,
                    decision=PolicyDecision.BLOCKED,
                    reason=f"Action blocked: Communication window limit ({policy.max_messages} messages) reached.",
                    policy_version=policy.version,
                    requires_human_approval=False,
                    violated_rules=violated_rules,
                )

        # Rule 4: Discount Ceiling
        if action_type == RecoveryActionType.OFFER_DISCOUNT or proposed_discount_pct > 0:
            if proposed_discount_pct > policy.max_discount_pct:
                violated_rules.append(
                    f"Discount ceiling violated: Proposed {proposed_discount_pct:.1f}% > allowed {policy.max_discount_pct:.1f}%"
                )
                return PolicyEvaluationResult(
                    allowed=False,
                    decision=PolicyDecision.REQUIRES_HUMAN_APPROVAL,
                    reason=f"Human approval required: Proposed discount of {proposed_discount_pct:.1f}% exceeds max {policy.max_discount_pct:.1f}%.",
                    policy_version=policy.version,
                    requires_human_approval=True,
                    violated_rules=violated_rules,
                )

        # Rule 5: High Value Human Approval Threshold
        if amount_at_risk >= policy.human_approval_threshold:
            return PolicyEvaluationResult(
                allowed=True,
                decision=PolicyDecision.REQUIRES_HUMAN_APPROVAL,
                reason=(
                    f"Human approval required: Transaction amount ₹{amount_at_risk:,.0f} "
                    f"meets or exceeds threshold of ₹{policy.human_approval_threshold:,.0f}."
                ),
                policy_version=policy.version,
                requires_human_approval=True,
                violated_rules=[],
            )

        # Rule 6: Unclassified / Unknown Failure Code
        if not code or code in ["unknown", "generic_error"]:
            return PolicyEvaluationResult(
                allowed=True,
                decision=PolicyDecision.REQUIRES_HUMAN_APPROVAL,
                reason="Human approval required: Unclassified or unknown failure code requires manual review.",
                policy_version=policy.version,
                requires_human_approval=True,
                violated_rules=[],
            )

        # All checks passed
        return PolicyEvaluationResult(
            allowed=True,
            decision=PolicyDecision.ALLOWED,
            reason=f"Action '{action_type.value}' is compliant with Policy v{policy.version}.",
            policy_version=policy.version,
            requires_human_approval=False,
            violated_rules=[],
        )
