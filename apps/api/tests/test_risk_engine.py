"""Unit tests for the Revenue Risk Scoring Engine."""
import pytest
from app.models.enums import CustomerSegment, RecoverySourceType, RiskCategory
from app.risk.engine import RevenueRiskEngine


def test_enterprise_high_value_assessment():
    """Test assessment of high-value enterprise invoice failure."""
    res = RevenueRiskEngine.assess_risk(
        amount=150000.0,
        failure_code="insufficient_funds",
        source_type=RecoverySourceType.OVERDUE_INVOICE,
        customer_segment=CustomerSegment.ENTERPRISE,
        lifetime_value=2000000.0,
        past_successful_payments=15,
        failed_attempts_count=1,
    )
    assert res.amount_at_risk == 150000.0
    assert res.recovery_probability >= 0.80
    assert res.priority_score >= 80.0
    assert res.risk_category == RiskCategory.CRITICAL
    assert any("Historical Value" in s or "track record" in s for s in res.positive_signals)


def test_transient_network_timeout():
    """Test assessment of transient bank network timeout."""
    res = RevenueRiskEngine.assess_risk(
        amount=12000.0,
        failure_code="network_timeout",
        source_type=RecoverySourceType.SUBSCRIPTION_DUNNING,
        customer_segment=CustomerSegment.SMB,
        lifetime_value=80000.0,
        past_successful_payments=6,
    )
    assert res.recovery_probability >= 0.85
    assert any("Transient error" in s for s in res.positive_signals)


def test_severe_fraud_failure():
    """Test assessment of fraud or stolen card."""
    res = RevenueRiskEngine.assess_risk(
        amount=5000.0,
        failure_code="fraud_suspected",
        source_type=RecoverySourceType.CHECKOUT_ABANDONMENT,
        customer_segment=CustomerSegment.RETAIL,
        lifetime_value=0.0,
        past_successful_payments=0,
        failed_attempts_count=2,
    )
    assert res.recovery_probability <= 0.10
    assert any("Severe failure code" in s for s in res.negative_signals)


def test_aged_invoice_penalty():
    """Test that heavily aged invoices receive appropriate probability penalties."""
    res_fresh = RevenueRiskEngine.assess_risk(
        amount=50000.0,
        failure_code="insufficient_funds",
        invoice_age_days=3,
    )
    res_aged = RevenueRiskEngine.assess_risk(
        amount=50000.0,
        failure_code="insufficient_funds",
        invoice_age_days=65,
    )
    assert res_aged.recovery_probability < res_fresh.recovery_probability
    assert any("Highly aged" in s for s in res_aged.negative_signals)


def test_promise_to_pay_boost():
    """Test that confirmed promise to pay increases recovery probability."""
    res_without = RevenueRiskEngine.assess_risk(
        amount=40000.0,
        failure_code="card_expired",
        has_promise_to_pay=False,
    )
    res_with = RevenueRiskEngine.assess_risk(
        amount=40000.0,
        failure_code="card_expired",
        has_promise_to_pay=True,
    )
    assert res_with.recovery_probability > res_without.recovery_probability
    assert any("Promise-to-Pay" in s for s in res_with.positive_signals)


def test_mandate_failure_codes_risk_scoring():
    """Test risk scoring across UPI/NACH mandate failure taxonomy."""
    # 1. NPCI Central Switch Downtime (Highest Tier Infra Issue)
    res_npci = RevenueRiskEngine.assess_risk(
        amount=20000.0,
        failure_code="npci_downtime",
        source_type=RecoverySourceType.MANDATE_FAILURE,
        customer_segment=CustomerSegment.SMB,
        past_successful_payments=5,
    )
    assert res_npci.recovery_probability >= 0.85
    assert any("Transient error" in s for s in res_npci.positive_signals)

    # 2. Bank Server Core Banking Outage
    res_bank = RevenueRiskEngine.assess_risk(
        amount=25000.0,
        failure_code="bank_server_error",
        source_type=RecoverySourceType.MANDATE_FAILURE,
        customer_segment=CustomerSegment.SMB,
        past_successful_payments=4,
    )
    assert res_bank.recovery_probability >= 0.80

    # 3. Scheduled Mandate Low Balance
    res_low_bal = RevenueRiskEngine.assess_risk(
        amount=15000.0,
        failure_code="low_balance_recurring",
        source_type=RecoverySourceType.MANDATE_FAILURE,
        customer_segment=CustomerSegment.RETAIL,
        past_successful_payments=2,
    )
    assert 0.50 <= res_low_bal.recovery_probability <= 0.70

    # 4. Mandate Limit Exceeded
    res_limit = RevenueRiskEngine.assess_risk(
        amount=50000.0,
        failure_code="mandate_amount_exceeded",
        source_type=RecoverySourceType.MANDATE_FAILURE,
        customer_segment=CustomerSegment.SMB,
        past_successful_payments=3,
    )
    assert 0.50 <= res_limit.recovery_probability <= 0.70

    # 5. Mandate Expired (Requires renewal, not auto-retry)
    res_exp = RevenueRiskEngine.assess_risk(
        amount=12000.0,
        failure_code="mandate_expired",
        source_type=RecoverySourceType.MANDATE_FAILURE,
        customer_segment=CustomerSegment.RETAIL,
        past_successful_payments=0,
    )
    assert res_exp.recovery_probability <= 0.20
    assert any("Severe failure code" in s for s in res_exp.negative_signals)

    # 6. Mandate Revoked by Customer at Bank (Essentially unrecoverable via retry)
    res_revoked = RevenueRiskEngine.assess_risk(
        amount=18000.0,
        failure_code="mandate_revoked",
        source_type=RecoverySourceType.MANDATE_FAILURE,
        customer_segment=CustomerSegment.RETAIL,
        past_successful_payments=0,
    )
    assert res_revoked.recovery_probability <= 0.10
    assert any("Severe failure code" in s for s in res_revoked.negative_signals)
