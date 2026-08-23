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
        mandate_retry_window_hours=24,
        max_mandate_attempts_per_cycle=3,
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


def test_mandate_expired_and_revoked_block_retry_and_route_to_renewal(standard_policy):
    """Test that mandate_expired and mandate_revoked block retries and route to REQUEST_MANDATE_RENEWAL."""
    for failure_code in ["mandate_expired", "mandate_revoked"]:
        # RESEQUENCE_MANDATE_RETRY should be blocked
        res_retry = PolicyEngine.evaluate(
            policy=standard_policy,
            action_type=RecoveryActionType.RESEQUENCE_MANDATE_RETRY,
            amount_at_risk=15000.0,
            failure_code=failure_code,
            attempts_count=0,
        )
        assert res_retry.allowed is False
        assert res_retry.decision == PolicyDecision.BLOCKED
        assert "cannot be auto-retried" in res_retry.reason
        assert "REQUEST_MANDATE_RENEWAL" in res_retry.reason

        # Standard RETRY_PAYMENT should also be blocked
        res_payment_retry = PolicyEngine.evaluate(
            policy=standard_policy,
            action_type=RecoveryActionType.RETRY_PAYMENT,
            amount_at_risk=15000.0,
            failure_code=failure_code,
            attempts_count=0,
        )
        assert res_payment_retry.allowed is False
        assert res_payment_retry.decision == PolicyDecision.BLOCKED

        # REQUEST_MANDATE_RENEWAL must be allowed
        res_renewal = PolicyEngine.evaluate(
            policy=standard_policy,
            action_type=RecoveryActionType.REQUEST_MANDATE_RENEWAL,
            amount_at_risk=15000.0,
            failure_code=failure_code,
            attempts_count=0,
        )
        assert res_renewal.allowed is True
        assert res_renewal.decision == PolicyDecision.ALLOWED
        assert res_renewal.requires_human_approval is False


def test_mandate_retry_within_cooldown_window_blocked(standard_policy):
    """Test that a mandate retry attempted within the retry window is BLOCKED."""
    res = PolicyEngine.evaluate(
        policy=standard_policy,
        action_type=RecoveryActionType.RESEQUENCE_MANDATE_RETRY,
        amount_at_risk=18000.0,
        failure_code="npci_downtime",
        hours_since_last_attempt=12.0,  # Less than 24-hour window
        mandate_attempts_count=1,
    )
    assert res.allowed is False
    assert res.decision == PolicyDecision.BLOCKED
    assert "cooldown window" in res.reason or "window not met" in res.reason


def test_mandate_retry_after_window_and_under_cycle_cap_allowed(standard_policy):
    """Test that a mandate retry after the window with attempts under the per-cycle cap is ALLOWED."""
    res = PolicyEngine.evaluate(
        policy=standard_policy,
        action_type=RecoveryActionType.RESEQUENCE_MANDATE_RETRY,
        amount_at_risk=18000.0,
        failure_code="npci_downtime",
        hours_since_last_attempt=28.0,  # Greater than 24-hour window
        mandate_attempts_count=1,       # Under cap of 3
    )
    assert res.allowed is True
    assert res.decision == PolicyDecision.ALLOWED
    assert res.requires_human_approval is False
    assert len(res.violated_rules) == 0


def test_mandate_retry_cycle_cap_blocked(standard_policy):
    """Test that reaching max mandate attempts per cycle blocks further mandate retries."""
    res = PolicyEngine.evaluate(
        policy=standard_policy,
        action_type=RecoveryActionType.RESEQUENCE_MANDATE_RETRY,
        amount_at_risk=18000.0,
        failure_code="low_balance_recurring",
        hours_since_last_attempt=30.0,
        mandate_attempts_count=3,  # Reached cap of 3
    )
    assert res.allowed is False
    assert res.decision == PolicyDecision.BLOCKED
    assert "Maximum mandate cycle attempts" in res.reason
