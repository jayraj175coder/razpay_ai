# Bounded Policy Engine

The **Bounded Policy Engine** serves as the deterministic firewall between AI suggestions and live payment execution.

---

## 1. Core Policy Safeguards

| Policy Rule | Standard Constraint | Enforcement Mechanism |
|---|---|---|
| **Max Retry Cap** | Max 3 payment retries per billing cycle | Rejects retry if `failed_attempts >= max_payment_retries` |
| **Communication Limits** | Max 2 customer reminders in a 7-day window | Checks timestamp of past sent actions in `communication_window_hours` |
| **Discount Ceiling** | Max 5.0% discount on cart abandonment | Caps or blocks AI discount proposals exceeding `max_discount_pct` |
| **High-Value Threshold** | Any transaction >= ₹1,00,000 | Forces state `ESCALATED` for human operator approval |
| **Security Blacklist** | `fraud_suspected`, `stolen_card`, `account_frozen` | Strictly returns `BLOCKED` and transitions case to `STOPPED` |

---

## 2. Policy Evaluation Flow

```python
class PolicyEngine:
    @classmethod
    def evaluate(
        cls,
        case: RecoveryCase,
        proposed_action_type: RecoveryActionType,
        policy: RecoveryPolicy,
        proposed_delay_hours: int = 0,
        proposed_discount_pct: float = 0.0,
        customer_opt_out: bool = False,
    ) -> PolicyEvaluationResult:
        # 1. Customer Opt-Out Check
        # 2. Fraud & Security Code Check (Immediate Block)
        # 3. High-Value Threshold Check (Requires Human Sign-off)
        # 4. Max Retry Limit Check
        # 5. Communication Window Cap Check
        # 6. Max Discount Allowance Check
        # -> Returns PolicyEvaluationResult(decision, reason, violated_rules)
```

---

## 3. Dynamic Versioning & Auditability

Policies are versioned in `RecoveryPolicy` table (Policy v1, Policy v2). When an operator updates rules via the `/policies` dashboard:
1. The new version is stored with an incremented version number.
2. Previous versions are safely marked `is_active = False`.
3. An audit event is logged with actor `HUMAN_OPERATOR` and payload diff.
