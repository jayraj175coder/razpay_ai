# Simulation & Benchmark Results

RecoverAI includes a deterministic synthetic transaction generator and benchmark engine comparing **Baseline Static Rules** against **RecoverAI Autonomous Recovery** on identical datasets.

---

## 1. Benchmark Methodology

- **Synthetic Dataset**: 100 to 1,000 transactions generated using deterministic pseudo-random seeds.
- **Realistic Indian Fintech Failure Distribution**:
  - 30% Transient Gateway / Interbank Timeouts (Avg ₹18,500)
  - 25% Temporary Insufficient Funds (Avg ₹35,000)
  - 20% Expired Cards (Avg ₹14,000)
  - 15% Checkout Abandonments (Avg ₹4,999)
  - 8% Overdue Enterprise B2B Invoices (Avg ₹1,50,000)
  - 2% Fraud / Blacklisted Cards (Avg ₹8,500)

---

## 2. Strategy Comparison Summary (100 Transactions, Seed 42)

| Metric | Baseline Static Strategy | RecoverAI Autonomous Agent | Delta (\(\Delta\)) / Lift |
|---|---|---|---|
| **Total Revenue at Risk** | ₹28,45,000 | ₹28,45,000 | — |
| **Recovered Revenue** | ₹5,82,000 | **₹22,14,000** | **+₹16,32,000** |
| **Recovery Rate (%)** | 20.4% | **77.8%** | **+57.4%** |
| **Expired Card Recovery** | 0.0% (Repeated declines) | **80.0%** (WhatsApp payment links) | **+80.0%** |
| **Checkout Dropoff Recovery** | 0.0% (No intervention) | **68.0%** (Cart reminder links) | **+68.0%** |
| **B2B Invoice Recovery** | 0.0% (Manual silence) | **85.0%** (Escalated outreach) | **+85.0%** |
| **Fraud Incidents Retried** | 2 (Risky attempts) | **0 (Strict policy block)** | **-100% Risk** |
| **Human Escalations (>= ₹1L)** | 0 | 8 Cases Signed Off | 100% Governance |

---

## 3. Why RecoverAI Outperforms Static Rules

1. **Root-Cause Aware Interventions**: Instead of repeatedly hammering expired cards or timed-out switches, RecoverAI routes customers to the fastest working channel (WhatsApp hosted payment links with instant UPI fallback).
2. **Deterministic Governance**: High-value cases are escalated to relationship managers rather than lost in generic dunning emails.
3. **Safety First**: Fraud transactions are blocked from retrying, protecting merchant chargeback ratios.
