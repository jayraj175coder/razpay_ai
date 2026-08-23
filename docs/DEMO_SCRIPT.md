# 🎬 RecoverAI — Official Demo Video Walkthrough Script

**Track 03:** AI Revenue Recovery — Razorpay AI Builder Challenge  
**Target Duration:** ~2 Minutes 45 Seconds (165 Seconds)  
**Presenter:** Jayraj Sanas  
**Recommended Resolution:** 1080p (1920x1080) 60fps  

---

## ⏱️ Video Breakdown & Timestamped Cue Sheet

```
+-----------------------------------------------------------------------------------------------+
| 00:00 - 00:25 | 1. Introduction & The Problem (Dumb Dunning vs Contextual AI)                |
| 00:25 - 00:55 | 2. Real-Time Webhook Ingestion & 10-Node LangGraph Diagnosis                 |
| 00:55 - 01:25 | 3. Deterministic Policy Gate: Safe Allowance vs Guardrail Block               |
| 01:25 - 01:55 | 4. High-Value Human-in-the-Loop Governance (>= ₹1,00,000 Approval Queue)      |
| 01:55 - 02:25 | 5. Deterministic Side-by-Side Simulation Benchmark Engine (+57.4% Lift)      |
| 02:25 - 02:45 | 6. Cryptographic SHA-256 Audit Trail & Verified Financial Ledger             |
+-----------------------------------------------------------------------------------------------+
```

---

### Scene 1: Introduction & The Core Axiom (00:00 – 00:25)
- **Visual:** Full-screen web command center (`/dashboard`), showing live KPIs: Total Revenue at Risk (₹32.4L), Recovered (₹24.8L), Recovery Rate (76.5%), and Live Cases breakdown.
- **Presenter Voiceover:**
  > "Hi everyone, I'm excited to present **RecoverAI** for the Razorpay AI Builder Challenge.
  > 
  > Conventional revenue recovery relies on dumb, blind cron retries or spammy email blasts. They annoy VIP customers, repeatedly hammer expired cards, and risk fraud chargebacks.
  > 
  > RecoverAI is built on a single core axiom: **We use AI for deep root-cause reasoning and personalized outreach, while deterministic, hardcoded code governs all money math, retry caps, discount limits, and human approval firewalls.**"

---

### Scene 2: Real-Time Webhook Ingestion & LangGraph Diagnosis (00:25 – 00:55)
- **Visual:** Navigate to `/recovery`. Click on case `RCV-78901` (Acme Retail, ₹24,500, `SUBSCRIPTION_DUNNING` failure). Click the blue **"Run AI Diagnosis"** button.
- **Action:** Watch the 10-node LangGraph execution status badges illuminate live: `load_customer_context` $\rightarrow$ `diagnose` $\rightarrow$ `calculate_recovery_score` $\rightarrow$ `select_strategy`.
- **Presenter Voiceover:**
  > "Here’s a real subscription payment failure coming in via our SHA-256 deduplicated webhook pipeline. 
  > 
  > In one click, our 10-node LangGraph recovery agent investigates customer context, historical liquidity, and error telemetry. It diagnoses the root cause as a transient gateway timeout during high-volume bank traffic, calculates a high recovery probability of 92%, and proposes a 1-click WhatsApp payment link dispatch after a short cooldown window."

---

### Scene 3: Deterministic Policy Gate — Allowing vs Blocking Actions (00:55 – 01:25)
- **Visual:** Scroll to the **Policy Decision Card** on the Case Details page (`/recovery/RCV-78901`). Show the green **"ALLOWED"** status badge with verified rule checks.
- **Visual Transition:** Switch to another case `RCV-FRAUD-004` (Stolen Card Velocity Trigger, ₹8,500) showing a red **"BLOCKED"** badge.
- **Presenter Voiceover:**
  > "Notice what happens before any payment request is dispatched to the gateway: every action must pass through our **Deterministic Bounded Policy Engine**.
  > 
  > For Acme Retail, the action is **ALLOWED** because attempts and discount ceilings are compliant.
  > 
  > But if we look at a suspicious case like this fraud-velocity trigger, the Policy Engine **strictly blocks** automated retries with zero exceptions—preventing costly chargebacks and preserving merchant reputation."

---

### Scene 4: High-Value Governance & Human Approval Queue (01:25 – 01:55)
- **Visual:** Click on the top navigation bar item **"Approvals (/approvals)"**. Show the pending case `RCV-INV-9901` (Bharat Finserve, ₹1,50,000 Overdue Enterprise Invoice).
- **Action:** Click **"Review & Approve"**, enter note *"Verified with relationship manager"*, and click **"Approve Intervention"**.
- **Presenter Voiceover:**
  > "For B2B receivables and high-value transactions exceeding our policy safety threshold of ₹1,00,000, RecoverAI enforces **Human-in-the-Loop Governance**.
  > 
  > Instead of sending automated emails to an enterprise CFO, the case is routed to our Human Approvals Queue. Operators can review customer lifetime value, inspect AI recommendations, and authorize custom phone outreach or modify terms with a recorded audit signature."

---

### Scene 5: Side-by-Side Simulation Benchmark Engine (01:55 – 02:25)
- **Visual:** Navigate to **"Simulation (/simulation)"**. Select Batch Size: **100 Transactions**, Random Seed: **42**. Click **"Run Side-by-Side Benchmark"**.
- **Action:** Watch the dual progress bars and comparative metrics calculate side-by-side:
  - **Baseline Dumb Retries:** `20.4%` Recovery Rate | `₹4.56L` Recovered
  - **RecoverAI Agent:** `77.8%` Recovery Rate | `₹20.88L` Recovered
  - **Incremental Revenue Lift:** `+57.4%` Lift | `+₹16.32 Lakhs` Additional Revenue!
- **Presenter Voiceover:**
  > "To mathematically prove RecoverAI's effectiveness, we built a deterministic side-by-side benchmark simulator.
  > 
  > Over a representative batch of 100 failed transactions, blind cron retries recover only 20.4% because they fail on expired cards, dropoffs, and mandates. 
  > 
  > RecoverAI delivers a **77.8% recovery rate**—an **incremental lift of +57.4%** and over **₹16 Lakhs in recovered revenue per 100 cases**!"

---

### Scene 6: Cryptographic Audit Trail & Verified Financial Ledger (02:25 – 02:45)
- **Visual:** Navigate to **"Audit Ledger (/audit)"**. Show the table with SHA-256 `entry_hash` and `prev_hash` fields for every state transition, LLM diagnosis, and operator action.
- **Presenter Voiceover:**
  > "Finally, every transition, AI prompt metadata diff, and human approval is cryptographically chained in our immutable SHA-256 audit ledger—giving financial auditors 100% mathematical tamper evidence.
  > 
  > RecoverAI turns revenue leakage into predictable cash flow with complete peace of mind. Thank you!"

---

## 📋 Recording Checklist
- [x] Backend running on `http://localhost:8000` (auto-seeded with mock mode defaults)
- [x] Frontend running on `http://localhost:3000`
- [x] Browser zoom at 100% or 110% for crisp typography
- [x] Clear mic audio with no background noise
- [x] Cursor highlighter enabled
