"""Unit tests for the Recovery State Machine and Stopping Rules."""
import pytest
from app.models.enums import RecoveryState, RecoverySourceType, ActorType, RiskCategory
from app.models.recovery_case import RecoveryCase
from app.models.recovery_policy import RecoveryPolicy
from app.state_machine.machine import RecoveryStateMachine, StateTransitionError, StoppingRule


@pytest.fixture
def sample_case():
    return RecoveryCase(
        id="RCV-TEST-001",
        source_type=RecoverySourceType.PAYMENT_FAILURE,
        source_id="txn_test",
        customer_id="cust_1",
        amount_at_risk=50000.0,
        status=RecoveryState.DETECTED,
        recovered_amount=0.0,
    )


@pytest.fixture
def default_policy():
    return RecoveryPolicy(
        max_payment_retries=3,
        max_messages=2,
        communication_window_hours=168,
        max_discount_pct=5.0,
        human_approval_threshold=100000.0,
    )


def test_valid_linear_state_transitions(sample_case):
    """Test valid end-to-end recovery state machine flow."""
    # DETECTED -> DIAGNOSED
    audit1 = RecoveryStateMachine.transition(sample_case, RecoveryState.DIAGNOSED, ActorType.AI_AGENT)
    assert sample_case.status == RecoveryState.DIAGNOSED
    assert audit1.actor_type == ActorType.AI_AGENT

    # DIAGNOSED -> ACTION_PROPOSED
    RecoveryStateMachine.transition(sample_case, RecoveryState.ACTION_PROPOSED, ActorType.AI_AGENT)
    assert sample_case.status == RecoveryState.ACTION_PROPOSED

    # ACTION_PROPOSED -> POLICY_CHECK
    RecoveryStateMachine.transition(sample_case, RecoveryState.POLICY_CHECK, ActorType.POLICY_ENGINE)
    assert sample_case.status == RecoveryState.POLICY_CHECK

    # POLICY_CHECK -> APPROVED
    RecoveryStateMachine.transition(sample_case, RecoveryState.APPROVED, ActorType.POLICY_ENGINE)
    assert sample_case.status == RecoveryState.APPROVED

    # APPROVED -> EXECUTING
    RecoveryStateMachine.transition(sample_case, RecoveryState.EXECUTING, ActorType.RECOVERY_EXECUTOR)
    assert sample_case.status == RecoveryState.EXECUTING

    # EXECUTING -> AWAITING_RESULT
    RecoveryStateMachine.transition(sample_case, RecoveryState.AWAITING_RESULT, ActorType.RECOVERY_EXECUTOR)
    assert sample_case.status == RecoveryState.AWAITING_RESULT

    # AWAITING_RESULT -> RECOVERED
    sample_case.recovered_amount = sample_case.amount_at_risk
    RecoveryStateMachine.transition(sample_case, RecoveryState.RECOVERED, ActorType.RECOVERY_EXECUTOR)
    assert sample_case.status == RecoveryState.RECOVERED


def test_invalid_state_transition_raises_error(sample_case):
    """Test that invalid jumps are strictly blocked."""
    # DETECTED cannot jump directly to RECOVERED or EXECUTING
    with pytest.raises(StateTransitionError) as exc_info:
        RecoveryStateMachine.transition(sample_case, RecoveryState.RECOVERED)
    assert "Invalid state transition" in str(exc_info.value)
    assert sample_case.status == RecoveryState.DETECTED

    with pytest.raises(StateTransitionError):
        RecoveryStateMachine.transition(sample_case, RecoveryState.EXECUTING)


def test_terminal_state_cannot_transition(sample_case):
    """Test that terminal states RECOVERED and STOPPED reject any further transitions."""
    sample_case.status = RecoveryState.RECOVERED
    with pytest.raises(StateTransitionError):
        RecoveryStateMachine.transition(sample_case, RecoveryState.DIAGNOSED)

    sample_case.status = RecoveryState.STOPPED
    with pytest.raises(StateTransitionError):
        RecoveryStateMachine.transition(sample_case, RecoveryState.EXECUTING)


def test_escalation_and_approval_flow(sample_case):
    """Test human escalation path from policy check to approval."""
    sample_case.status = RecoveryState.POLICY_CHECK
    
    # POLICY_CHECK -> ESCALATED
    RecoveryStateMachine.transition(
        sample_case,
        RecoveryState.ESCALATED,
        actor_type=ActorType.POLICY_ENGINE,
        reason="Transaction > ₹1,00,000 threshold",
    )
    assert sample_case.status == RecoveryState.ESCALATED

    # ESCALATED -> APPROVED (By Human Operator)
    audit = RecoveryStateMachine.transition(
        sample_case,
        RecoveryState.APPROVED,
        actor_type=ActorType.HUMAN_OPERATOR,
        actor_id="operator_deepa@company.com",
        reason="Approved after relationship manager verification",
    )
    assert sample_case.status == RecoveryState.APPROVED
    assert audit.actor_type == ActorType.HUMAN_OPERATOR
    assert audit.actor_id == "operator_deepa@company.com"


def test_stopping_rules(sample_case, default_policy):
    """Test all stopping rules."""
    # 1. Max retries reached
    stop, rule, reason = RecoveryStateMachine.evaluate_stopping_rules(
        sample_case, default_policy, attempts_count=3
    )
    assert stop is True
    assert rule == StoppingRule.MAX_RETRIES_EXCEEDED

    # 2. Max messages reached
    stop, rule, reason = RecoveryStateMachine.evaluate_stopping_rules(
        sample_case, default_policy, attempts_count=1, messages_sent=2
    )
    assert stop is True
    assert rule == StoppingRule.MAX_MESSAGES_EXCEEDED

    # 3. Fraud suspected
    stop, rule, reason = RecoveryStateMachine.evaluate_stopping_rules(
        sample_case, default_policy, attempts_count=1, is_fraud_suspected=True
    )
    assert stop is True
    assert rule == StoppingRule.FRAUD_RISK_DETECTED

    # 4. Customer opt out
    stop, rule, reason = RecoveryStateMachine.evaluate_stopping_rules(
        sample_case, default_policy, customer_opted_out=True
    )
    assert stop is True
    assert rule == StoppingRule.CUSTOMER_OPT_OUT

    # 5. Normal active case -> should not stop
    stop, rule, reason = RecoveryStateMachine.evaluate_stopping_rules(
        sample_case, default_policy, attempts_count=1, messages_sent=1
    )
    assert stop is False
    assert rule is None


def test_awaiting_mandate_renewal_transitions(sample_case):
    """Test transitions into and out of AWAITING_MANDATE_RENEWAL."""
    # From POLICY_CHECK -> AWAITING_MANDATE_RENEWAL
    sample_case.status = RecoveryState.POLICY_CHECK
    RecoveryStateMachine.transition(
        sample_case,
        RecoveryState.AWAITING_MANDATE_RENEWAL,
        actor_type=ActorType.POLICY_ENGINE,
        reason="Mandate expired; waiting for customer e-mandate re-authorization",
    )
    assert sample_case.status == RecoveryState.AWAITING_MANDATE_RENEWAL

    # AWAITING_MANDATE_RENEWAL -> RECOVERED
    sample_case.recovered_amount = sample_case.amount_at_risk
    RecoveryStateMachine.transition(
        sample_case,
        RecoveryState.RECOVERED,
        actor_type=ActorType.RECOVERY_EXECUTOR,
        reason="Customer completed mandate renewal and payment was collected",
    )
    assert sample_case.status == RecoveryState.RECOVERED

    # From ACTION_PROPOSED -> AWAITING_MANDATE_RENEWAL -> STOPPED
    sample_case.status = RecoveryState.ACTION_PROPOSED
    RecoveryStateMachine.transition(
        sample_case,
        RecoveryState.AWAITING_MANDATE_RENEWAL,
        actor_type=ActorType.AI_AGENT,
    )
    assert sample_case.status == RecoveryState.AWAITING_MANDATE_RENEWAL

    RecoveryStateMachine.transition(
        sample_case,
        RecoveryState.STOPPED,
        actor_type=ActorType.SYSTEM,
        reason="Renewal window timed out",
    )
    assert sample_case.status == RecoveryState.STOPPED
