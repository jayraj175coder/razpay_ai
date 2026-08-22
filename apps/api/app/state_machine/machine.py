"""Deterministic State Machine and Stopping Rules Engine for Recovery Cases."""
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple
from app.models.enums import RecoveryState, ActorType
from app.models.recovery_case import RecoveryCase
from app.models.recovery_policy import RecoveryPolicy
from app.models.audit_log import AuditLog


class StateTransitionError(Exception):
    """Raised when an invalid state transition is attempted."""
    def __init__(self, current_state: RecoveryState, attempted_state: RecoveryState, reason: Optional[str] = None):
        msg = f"Invalid state transition from '{current_state.value}' to '{attempted_state.value}'"
        if reason:
            msg += f": {reason}"
        super().__init__(msg)
        self.current_state = current_state
        self.attempted_state = attempted_state
        self.reason = reason


class StoppingRule(str, Enum):
    PAYMENT_RECOVERED = "PAYMENT_RECOVERED"
    MAX_RETRIES_EXCEEDED = "MAX_RETRIES_EXCEEDED"
    MAX_MESSAGES_EXCEEDED = "MAX_MESSAGES_EXCEEDED"
    FRAUD_RISK_DETECTED = "FRAUD_RISK_DETECTED"
    CUSTOMER_OPT_OUT = "CUSTOMER_OPT_OUT"
    POLICY_PROHIBITED = "POLICY_PROHIBITED"
    HUMAN_ESCALATION_REQUIRED = "HUMAN_ESCALATION_REQUIRED"


# Explicit valid transition matrix
VALID_TRANSITIONS: Dict[RecoveryState, Set[RecoveryState]] = {
    RecoveryState.DETECTED: {
        RecoveryState.DIAGNOSED,
        RecoveryState.STOPPED,
    },
    RecoveryState.DIAGNOSED: {
        RecoveryState.ACTION_PROPOSED,
        RecoveryState.ESCALATED,
        RecoveryState.STOPPED,
    },
    RecoveryState.ACTION_PROPOSED: {
        RecoveryState.POLICY_CHECK,
        RecoveryState.ESCALATED,
        RecoveryState.STOPPED,
    },
    RecoveryState.POLICY_CHECK: {
        RecoveryState.APPROVED,
        RecoveryState.REJECTED,
        RecoveryState.ESCALATED,
        RecoveryState.STOPPED,
    },
    RecoveryState.APPROVED: {
        RecoveryState.EXECUTING,
        RecoveryState.STOPPED,
    },
    RecoveryState.REJECTED: {
        RecoveryState.ACTION_PROPOSED,
        RecoveryState.ESCALATED,
        RecoveryState.STOPPED,
    },
    RecoveryState.EXECUTING: {
        RecoveryState.AWAITING_RESULT,
        RecoveryState.RECOVERED,
        RecoveryState.FAILED,
        RecoveryState.ESCALATED,
        RecoveryState.STOPPED,
    },
    RecoveryState.AWAITING_RESULT: {
        RecoveryState.RECOVERED,
        RecoveryState.FAILED,
        RecoveryState.RETRY_SCHEDULED,
        RecoveryState.ESCALATED,
        RecoveryState.STOPPED,
    },
    RecoveryState.RETRY_SCHEDULED: {
        RecoveryState.POLICY_CHECK,
        RecoveryState.EXECUTING,
        RecoveryState.ESCALATED,
        RecoveryState.STOPPED,
    },
    RecoveryState.ESCALATED: {
        RecoveryState.APPROVED,
        RecoveryState.REJECTED,
        RecoveryState.STOPPED,
    },
    RecoveryState.FAILED: {
        RecoveryState.RETRY_SCHEDULED,
        RecoveryState.ESCALATED,
        RecoveryState.STOPPED,
    },
    # Terminal states
    RecoveryState.RECOVERED: set(),
    RecoveryState.STOPPED: set(),
}


class RecoveryStateMachine:
    """Deterministic state transition controller and stopping rule evaluator."""

    @classmethod
    def can_transition(cls, from_state: RecoveryState, to_state: RecoveryState) -> bool:
        """Check if transition from from_state to to_state is allowed."""
        return to_state in VALID_TRANSITIONS.get(from_state, set())

    @classmethod
    def transition(
        cls,
        case: RecoveryCase,
        to_state: RecoveryState,
        actor_type: ActorType = ActorType.SYSTEM,
        actor_id: Optional[str] = None,
        reason: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> AuditLog:
        """
        Validate and execute state transition on RecoveryCase, generating an immutable AuditLog.
        """
        if not cls.can_transition(case.status, to_state):
            raise StateTransitionError(
                current_state=case.status,
                attempted_state=to_state,
                reason=f"Transition from {case.status.value} to {to_state.value} is not permitted by state machine.",
            )

        prev_state = case.status
        case.status = to_state

        # If entering STOPPED, record stopping reason
        if to_state == RecoveryState.STOPPED and reason:
            case.stopping_reason = reason

        audit_log = AuditLog(
            case_id=case.id,
            actor_type=actor_type,
            actor_id=actor_id,
            action=f"STATE_TRANSITION_{prev_state.value}_TO_{to_state.value}",
            reason=reason or f"State changed from {prev_state.value} to {to_state.value}",
            metadata_json={
                "from_state": prev_state.value,
                "to_state": to_state.value,
                **(metadata or {}),
            },
        )
        return audit_log

    @classmethod
    def evaluate_stopping_rules(
        cls,
        case: RecoveryCase,
        policy: RecoveryPolicy,
        attempts_count: int = 0,
        messages_sent: int = 0,
        is_fraud_suspected: bool = False,
        customer_opted_out: bool = False,
    ) -> Tuple[bool, Optional[StoppingRule], Optional[str]]:
        """
        Deterministically evaluates whether recovery on this case MUST stop immediately.
        
        Returns:
            (should_stop: bool, rule: Optional[StoppingRule], explanation: Optional[str])
        """
        # Rule 1: Payment already recovered
        if case.recovered_amount >= case.amount_at_risk and case.amount_at_risk > 0:
            return True, StoppingRule.PAYMENT_RECOVERED, "Full revenue has already been recovered."

        # Rule 2: Fraud / Security Risk
        if is_fraud_suspected:
            return True, StoppingRule.FRAUD_RISK_DETECTED, "Fraud or security risk detected on transaction. Automated actions prohibited."

        # Rule 3: Customer Opt-Out
        if customer_opted_out:
            return True, StoppingRule.CUSTOMER_OPT_OUT, "Customer has opted out of automated communications."

        # Rule 4: Maximum payment retries reached
        if attempts_count >= policy.max_payment_retries:
            return (
                True,
                StoppingRule.MAX_RETRIES_EXCEEDED,
                f"Maximum allowed payment retries ({policy.max_payment_retries}) reached.",
            )

        # Rule 5: Communication limit exceeded
        if messages_sent >= policy.max_messages:
            return (
                True,
                StoppingRule.MAX_MESSAGES_EXCEEDED,
                f"Maximum communication limit ({policy.max_messages} per window) reached.",
            )

        return False, None, None
