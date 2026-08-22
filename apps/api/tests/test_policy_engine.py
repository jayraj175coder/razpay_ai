"""Unit tests for the Bounded Policy Engine."""
import pytest
from app.models.enums import PolicyDecision, RecoveryActionType
from app.models.recovery_policy import RecoveryPolicy
from app.policies.engine import PolicyEngine


@pytest.fixture
def standard_policy():
    return RecoveryPolicy(
        version=1,
        max_payment_retries=3,
        max_messages=2,
        communication_window_hours=168,
        max_discount_pct=5.0,
        human_approval_threshold=100000.0,
    )


def test_compliant_retry_action(standard_policy):
    """Test retry payment within policy bounds."""
    res = PolicyEngine.evaluate(
        policy=standard_policy,
        action_type=RecoveryActionType.RETRY_PAYMENT,
        amount_at_risk=25000.0,
        failure_code="network_timeout",
        attempts_count=1,
    )
    assert res.allowed is True
    assert res.decision == PolicyDecision.ALLOWED
    assert res.requires_human_approval is False
    assert len(res.violated_rules) == 0


def test_max_retries_boundary_block(standard_policy):
    """Test blocking retry when 3 attempts have already been made."""
    res = PolicyEngine.evaluate(
        policy=standard_policy,
        action_type=RecoveryActionType.RETRY_PAYMENT,
        amount_at_risk=15000.0,
        failure_code="insufficient_funds",
        attempts_count=3,
    )
    assert res.allowed is False
    assert res.decision == PolicyDecision.BLOCKED
    assert "Maximum retries limit" in res.reason


def test_communication_limit_block(standard_policy):
    """Test blocking reminders when message limit is reached."""
    res = PolicyEngine.evaluate(
        policy=standard_policy,
        action_type=RecoveryActionType.SEND_PAYMENT_REMINDER,
        amount_at_risk=10000.0,
        failure_code="card_expired",
        messages_sent=2,
    )
    assert res.allowed is False
    assert res.decision == PolicyDecision.BLOCKED
    assert "Communication window limit" in res.reason


def test_security_fraud_blocklist(standard_policy):
    """Test that fraud suspected is strictly blocked from auto recovery."""
    res = PolicyEngine.evaluate(
        policy=standard_policy,
        action_type=RecoveryActionType.RETRY_PAYMENT,
        amount_at_risk=5000.0,
        failure_code="fraud_suspected",
        attempts_count=0,
    )
    assert res.allowed is False
    assert res.decision == PolicyDecision.BLOCKED
    assert "Security blocklist" in res.reason


def test_high_value_human_approval_gate(standard_policy):
    """Test that transactions >= ₹1,00,000 trigger human approval gate."""
    res = PolicyEngine.evaluate(
        policy=standard_policy,
        action_type=RecoveryActionType.RETRY_PAYMENT,
        amount_at_risk=125000.0,
        failure_code="insufficient_funds",
        attempts_count=0,
    )
    assert res.decision == PolicyDecision.REQUIRES_HUMAN_APPROVAL
    assert res.requires_human_approval is True
    assert "meets or exceeds threshold" in res.reason


def test_discount_ceiling_violation(standard_policy):
    """Test that discounts over 5% require human approval."""
    res = PolicyEngine.evaluate(
        policy=standard_policy,
        action_type=RecoveryActionType.OFFER_DISCOUNT,
        amount_at_risk=20000.0,
        failure_code="checkout_abandoned",
        proposed_discount_pct=10.0,
    )
    assert res.decision == PolicyDecision.REQUIRES_HUMAN_APPROVAL
    assert res.requires_human_approval is True
    assert any("Discount ceiling" in r for r in res.violated_rules)
