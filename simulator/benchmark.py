"""Side-by-Side Recovery Benchmark Engine: Baseline vs RecoverAI."""
import random
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from simulator.generator import SyntheticTransactionGenerator, SyntheticTransaction


@dataclass
class BenchmarkResult:
    dataset_size: int
    seed: int
    total_revenue_at_risk: float
    baseline_recovered_revenue: float
    recoverai_recovered_revenue: float
    incremental_recovered_revenue: float
    baseline_recovery_rate_pct: float
    recoverai_recovery_rate_pct: float
    incremental_recovery_rate_pct: float
    automated_interventions_count: int
    human_escalations_count: int
    policy_blocked_count: int
    breakdown_by_category: List[Dict[str, Any]] = field(default_factory=list)
    sample_cases: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "dataset_size": self.dataset_size,
            "seed": self.seed,
            "total_revenue_at_risk": round(self.total_revenue_at_risk, 2),
            "baseline_recovered_revenue": round(self.baseline_recovered_revenue, 2),
            "recoverai_recovered_revenue": round(self.recoverai_recovered_revenue, 2),
            "incremental_recovered_revenue": round(self.incremental_recovered_revenue, 2),
            "baseline_recovery_rate_pct": round(self.baseline_recovery_rate_pct, 2),
            "recoverai_recovery_rate_pct": round(self.recoverai_recovery_rate_pct, 2),
            "incremental_recovery_rate_pct": round(self.incremental_recovery_rate_pct, 2),
            "automated_interventions_count": self.automated_interventions_count,
            "human_escalations_count": self.human_escalations_count,
            "policy_blocked_count": self.policy_blocked_count,
            "breakdown_by_category": self.breakdown_by_category,
            "sample_cases": self.sample_cases,
        }


class RecoveryBenchmarkRunner:
    """Executes deterministic side-by-side comparison between baseline recovery and RecoverAI."""

    @classmethod
    def run_benchmark(
        cls, count: int = 100, seed: int = 42, mandate_ratio: Optional[float] = None
    ) -> BenchmarkResult:
        transactions = SyntheticTransactionGenerator.generate_batch(count=count, seed=seed, mandate_ratio=mandate_ratio)
        rng = random.Random(seed + 1000)

        total_risk = sum(t.amount for t in transactions)
        baseline_recovered = 0.0
        recoverai_recovered = 0.0

        auto_interventions = 0
        human_escalations = 0
        policy_blocks = 0

        breakdown_stats: Dict[str, Dict[str, float]] = {}
        sample_cases: List[Dict[str, Any]] = []

        for t in transactions:
            code = t.failure_code
            amt = t.amount

            if code not in breakdown_stats:
                breakdown_stats[code] = {
                    "at_risk": 0.0,
                    "baseline_rec": 0.0,
                    "recoverai_rec": 0.0,
                    "count": 0,
                }
            breakdown_stats[code]["at_risk"] += amt
            breakdown_stats[code]["count"] += 1

            # -------------------------------------------------------------
            # 1. BASELINE STRATEGY (Blind immediate retry, no smart routing)
            # -------------------------------------------------------------
            baseline_success = False
            if t.is_fraud:
                # Blind retry attempted on fraud (risky) -> declines
                baseline_success = False
            elif code in ["card_expired", "mandate_expired", "mandate_revoked"]:
                # Blind retry fails deterministically because card/mandate is expired or revoked
                baseline_success = False
            elif code == "mandate_amount_exceeded":
                # Blind retry with unchanged excessive amount fails deterministically
                baseline_success = False
            elif code == "checkout_abandoned":
                # No cart abandonment recovery system in baseline
                baseline_success = False
            elif code == "network_timeout":
                # Blind immediate retry during congested window
                baseline_success = rng.random() < 0.38
            elif code in ["npci_downtime", "bank_server_error"]:
                # Blind immediate retry during central/bank switch outage fails with high probability
                baseline_success = rng.random() < 0.22
            elif code in ["insufficient_funds", "low_balance_recurring"]:
                # Blind immediate retry before balance reload
                baseline_success = rng.random() < 0.18
            else:
                baseline_success = rng.random() < 0.20

            if baseline_success:
                baseline_recovered += amt
                breakdown_stats[code]["baseline_rec"] += amt

            # -------------------------------------------------------------
            # 2. RECOVERAI STRATEGY (AI Reasoning + Bounded Policy Engine)
            # -------------------------------------------------------------
            recoverai_success = False
            action_taken = "NONE"
            policy_decision = "ALLOWED"

            if t.is_fraud:
                # Policy Engine strictly blocks automated actions
                policy_blocks += 1
                policy_decision = "BLOCKED"
                action_taken = "POLICY_BLOCKED_FRAUD"
                recoverai_success = False

            elif code in ["mandate_expired", "mandate_revoked"]:
                # Policy Gate strictly blocks auto-retries on expired/revoked mandates; routes to renewal
                auto_interventions += 1
                action_taken = "REQUEST_MANDATE_RENEWAL"
                policy_decision = "ALLOWED"
                # Multi-channel 1-click mandate re-authorization / renewal workflow
                recoverai_success = rng.random() < (0.72 if code == "mandate_expired" else 0.42)

            elif amt >= 100000.0:
                # Policy Gate: High value human escalation
                human_escalations += 1
                policy_decision = "REQUIRES_HUMAN_APPROVAL"
                action_taken = "HUMAN_ESCALATED_CALL"
                # Relationship manager outreach achieves 85% success on enterprise accounts
                recoverai_success = rng.random() < 0.85

            elif code in ["npci_downtime", "bank_server_error"]:
                # Resequence mandate retry aligned with NPCI settlement window & bank recovery
                auto_interventions += 1
                action_taken = "RESEQUENCE_MANDATE_RETRY"
                recoverai_success = rng.random() < 0.92

            elif code in ["low_balance_recurring", "mandate_amount_exceeded"]:
                # Resequence mandate retry with cycle cooldown / smart split
                auto_interventions += 1
                action_taken = "RESEQUENCE_MANDATE_RETRY"
                recoverai_success = rng.random() < 0.78

            elif code == "network_timeout":
                # Smart off-peak retry (low traffic window)
                auto_interventions += 1
                action_taken = "SMART_OFFPEAK_RETRY"
                recoverai_success = rng.random() < 0.90

            elif code == "insufficient_funds":
                # Timed dunning retry (payroll cycle / post balance reload)
                auto_interventions += 1
                action_taken = "TIMED_DUNNING_RETRY"
                recoverai_success = rng.random() < 0.74

            elif code == "card_expired":
                # Multi-channel 1-click Razorpay payment link (UPI/Netbanking fallback)
                auto_interventions += 1
                action_taken = "WHATSAPP_PAYMENT_LINK"
                recoverai_success = rng.random() < 0.80

            elif code == "checkout_abandoned":
                # Instant cart restoration reminder with payment link
                auto_interventions += 1
                action_taken = "CART_RECOVERY_EMAIL"
                recoverai_success = rng.random() < 0.68

            else:
                auto_interventions += 1
                action_taken = "STANDARD_RECOVERY"
                recoverai_success = rng.random() < 0.65

            if recoverai_success:
                recoverai_recovered += amt
                breakdown_stats[code]["recoverai_rec"] += amt

            # Record sample cases for table (first 25)
            if len(sample_cases) < 25:
                sample_cases.append({
                    "id": t.id,
                    "customer_name": t.customer_name,
                    "customer_segment": t.customer_segment,
                    "amount": t.amount,
                    "failure_code": code,
                    "baseline_recovered": baseline_success,
                    "recoverai_recovered": recoverai_success,
                    "action_taken": action_taken,
                    "policy_decision": policy_decision,
                })

        incremental_revenue = recoverai_recovered - baseline_recovered
        baseline_rate = (baseline_recovered / total_risk * 100.0) if total_risk > 0 else 0.0
        recoverai_rate = (recoverai_recovered / total_risk * 100.0) if total_risk > 0 else 0.0
        incremental_rate = recoverai_rate - baseline_rate

        breakdown_list = [
            {
                "failure_code": k,
                "case_count": int(v["count"]),
                "amount_at_risk": round(v["at_risk"], 2),
                "baseline_recovered": round(v["baseline_rec"], 2),
                "recoverai_recovered": round(v["recoverai_rec"], 2),
                "incremental_recovered": round(v["recoverai_rec"] - v["baseline_rec"], 2),
                "baseline_rate": round((v["baseline_rec"] / v["at_risk"] * 100.0) if v["at_risk"] > 0 else 0.0, 1),
                "recoverai_rate": round((v["recoverai_rec"] / v["at_risk"] * 100.0) if v["at_risk"] > 0 else 0.0, 1),
            }
            for k, v in breakdown_stats.items()
        ]

        return BenchmarkResult(
            dataset_size=count,
            seed=seed,
            total_revenue_at_risk=total_risk,
            baseline_recovered_revenue=baseline_recovered,
            recoverai_recovered_revenue=recoverai_recovered,
            incremental_recovered_revenue=incremental_revenue,
            baseline_recovery_rate_pct=baseline_rate,
            recoverai_recovery_rate_pct=recoverai_rate,
            incremental_recovery_rate_pct=incremental_rate,
            automated_interventions_count=auto_interventions,
            human_escalations_count=human_escalations,
            policy_blocked_count=policy_blocks,
            breakdown_by_category=breakdown_list,
            sample_cases=sample_cases,
        )
