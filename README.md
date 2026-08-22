# RecoverAI — Production-Grade AI Revenue Recovery Platform

> **Detect revenue leakage. Diagnose why it happened. Decide the safest intervention. Recover the money. Prove the outcome.**

**RecoverAI** is an AI-powered revenue recovery platform designed for **Razorpay AI Builder Challenge — Track 03: AI Revenue Recovery**.

It continuously analyzes failed, delayed, abandoned, and at-risk payment events, determines the most likely recovery opportunity, selects a compliant intervention, executes the recovery workflow, and records the financial outcome in an auditable ledger.

The core design principle is simple:

> **AI decides what is likely to work. Deterministic systems decide what is allowed to happen.**

---

## 🎯 Problem

Payment failures do not always mean lost customers.

Revenue can slip away because of:

* Temporary payment failures
* Expired cards
* Insufficient funds
* Authentication failures
* Abandoned checkouts
* Repeated payment retries
* Customer intent changes
* Delayed payments
* Customers who promise to pay later
* High-value transactions requiring human intervention

Traditional retry systems treat these events similarly.

RecoverAI instead answers:

> **Who is likely to recover, why did the payment fail, what should we do next, and how much revenue was actually recovered?**

---

# 💡 Solution

RecoverAI converts raw payment events into an intelligent recovery pipeline:

```text
Payment Event
     ↓
Revenue Risk Detection
     ↓
Customer / Transaction Diagnosis
     ↓
AI Recovery Strategy
     ↓
Deterministic Policy Validation
     ↓
Recovery Execution
     ↓
Payment Confirmation
     ↓
Financial Reconciliation
     ↓
Recovery Analytics
```

The system does **not** allow an LLM to directly move money or bypass financial policies.

Instead:

```text
             ┌───────────────────────┐
             │     AI / LLM Layer    │
             │                       │
             │ • Diagnose failure   │
             │ • Predict intent     │
             │ • Select strategy    │
             │ • Generate message   │
             └──────────┬────────────┘
                        │
                        ▼
             ┌───────────────────────┐
             │  Deterministic Layer │
             │                       │
             │ • Policy validation  │
             │ • Retry limits       │
             │ • Discount limits    │
             │ • Approval gates     │
             │ • State validation   │
             └──────────┬────────────┘
                        │
                        ▼
             ┌───────────────────────┐
             │ Financial Execution  │
             │                       │
             │ • Payment attempt    │
             │ • Webhook processing │
             │ • Reconciliation     │
             │ • Audit ledger       │
             └───────────────────────┘
```

This separation makes RecoverAI **safer, explainable, testable, and production-oriented**.

---

# 🏛️ System Architecture

```mermaid
flowchart TB

    %% =========================
    %% CLIENT
    %% =========================

    U["Revenue Operations Team"]

    WEB["Next.js Command Center<br/>React + Tailwind + Recharts"]

    U --> WEB

    %% =========================
    %% API
    %% =========================

    API["FastAPI Application<br/>REST APIs + Webhooks + SSE"]

    WEB -->|"REST / SSE"| API

    %% =========================
    %% INGESTION
    %% =========================

    INGEST["Payment Event Ingestion"]

    API --> INGEST

    EVENT["Payment Events<br/>Failed • Abandoned • Delayed • At-Risk"]

    EVENT --> INGEST

    %% =========================
    %% RISK
    %% =========================

    RISK["Revenue Risk Engine<br/>Risk Score + Recovery Opportunity"]

    INGEST --> RISK

    %% =========================
    %% AI
    %% =========================

    GRAPH["LangGraph Recovery Agent"]

    DIAG["Failure Diagnosis"]
    INTENT["Customer Intent Analysis"]
    STRATEGY["Recovery Strategy Selection"]
    MESSAGE["Recovery Message Generation"]

    RISK --> GRAPH

    GRAPH --> DIAG
    DIAG --> INTENT
    INTENT --> STRATEGY
    STRATEGY --> MESSAGE

    %% =========================
    %% POLICY
    %% =========================

    POLICY["Deterministic Policy Engine"]

    LIMITS["Retry / Frequency Limits"]
    DISCOUNT["Discount Constraints"]
    APPROVAL["Human Approval Gates"]
    SAFETY["Financial Safety Rules"]

    STRATEGY --> POLICY

    POLICY --> LIMITS
    POLICY --> DISCOUNT
    POLICY --> APPROVAL
    POLICY --> SAFETY

    %% =========================
    %% STATE
    %% =========================

    STATE["Recovery State Machine"]

    POLICY --> STATE

    S1["DETECTED"]
    S2["DIAGNOSED"]
    S3["POLICY_CHECK"]
    S4["EXECUTING"]
    S5["RECOVERED"]
    S6["FAILED / ESCALATED"]

    STATE --> S1
    S1 --> S2
    S2 --> S3
    S3 --> S4
    S4 --> S5
    S4 --> S6

    %% =========================
    %% EXECUTION
    %% =========================

    PROVIDER["Payment Provider Sandbox<br/>Mock / Razorpay-ready"]

    STATE --> PROVIDER

    PROVIDER -->|"Payment Result / Webhook"| API

    %% =========================
    %% DATA
    %% =========================

    DB["PostgreSQL<br/>Recovery Ledger + Operational Data"]

    AUDIT["Immutable Audit Trail"]

    API --> DB
    STATE --> DB
    PROVIDER --> DB
    POLICY --> AUDIT
    STATE --> AUDIT
    API --> AUDIT

    AUDIT --> DB

    %% =========================
    %% ANALYTICS
    %% =========================

    ANALYTICS["Recovery Analytics"]

    DB --> ANALYTICS
    ANALYTICS --> WEB

    %% =========================
    %% SIMULATOR
    %% =========================

    SIM["Synthetic Revenue Simulator"]

    SIM --> EVENT
    SIM --> DB

    %% =========================
    %% STYLING
    %% =========================

    classDef frontend fill:#111827,color:#fff,stroke:#374151;
    classDef backend fill:#1f2937,color:#fff,stroke:#4b5563;
    classDef ai fill:#312e81,color:#fff,stroke:#6366f1;
    classDef deterministic fill:#14532d,color:#fff,stroke:#22c55e;
    classDef database fill:#7c2d12,color:#fff,stroke:#fb923c;
    classDef provider fill:#164e63,color:#fff,stroke:#22d3ee;

    class WEB frontend;
    class API,INGEST,RISK,ANALYTICS backend;
    class GRAPH,DIAG,INTENT,STRATEGY,MESSAGE ai;
    class POLICY,LIMITS,DISCOUNT,APPROVAL,SAFETY,STATE,S1,S2,S3,S4,S5,S6 deterministic;
    class DB,AUDIT database;
    class PROVIDER provider;
```

---

# 🔄 End-to-End Recovery Flow

```mermaid
sequenceDiagram

    participant P as Payment Provider
    participant API as FastAPI
    participant R as Risk Engine
    participant AI as LangGraph Agent
    participant PE as Policy Engine
    participant SM as State Machine
    participant L as Ledger
    participant UI as Command Center

    P->>API: Payment failure webhook

    API->>API: Validate + idempotency check

    API->>R: Analyze transaction

    R->>R: Calculate recovery opportunity

    R->>AI: Customer + transaction context

    AI->>AI: Diagnose root cause
    AI->>AI: Analyze customer intent
    AI->>AI: Select recovery strategy

    AI->>PE: Proposed intervention

    PE->>PE: Validate financial policies

    alt Policy Approved
        PE->>SM: Execute recovery
        SM->>P: Initiate recovery action
        P-->>API: Payment result

        API->>L: Reconcile transaction

        L->>UI: Verified recovery outcome
        UI-->>UI: Update recovery dashboard

    else Policy Rejected
        PE->>SM: Escalate / stop
        SM->>L: Record rejected action
        L->>UI: Show policy decision
    end
```

---

# 🧠 AI Recovery Agent

RecoverAI uses a **LangGraph-based agent workflow** instead of a single unrestricted LLM call.

### Agent Pipeline

```text
                    ┌────────────────────┐
                    │ Payment Event      │
                    └─────────┬──────────┘
                              ↓
                    ┌────────────────────┐
                    │ Context Builder     │
                    │ Customer + Payment │
                    └─────────┬──────────┘
                              ↓
                    ┌────────────────────┐
                    │ Failure Diagnosis  │
                    └─────────┬──────────┘
                              ↓
                    ┌────────────────────┐
                    │ Intent Analysis    │
                    └─────────┬──────────┘
                              ↓
                    ┌────────────────────┐
                    │ Strategy Selector  │
                    └─────────┬──────────┘
                              ↓
                    ┌────────────────────┐
                    │ Policy Validation  │
                    └─────────┬──────────┘
                              ↓
                    ┌────────────────────┐
                    │ Recovery Action    │
                    └─────────┬──────────┘
                              ↓
                    ┌────────────────────┐
                    │ Outcome Evaluation │
                    └────────────────────┘
```

### Example Strategies

| Situation                           | AI Recommendation       | Deterministic Guard |
| ----------------------------------- | ----------------------- | ------------------- |
| Temporary payment failure           | Retry later             | Retry ≤ 3           |
| Customer likely to complete payment | Reminder                | Frequency limit     |
| High-value transaction              | Assisted recovery       | Human approval      |
| Price-sensitive customer            | Incentive               | Discount ≤ 5%       |
| Customer promises later payment     | Promise-to-pay workflow | Follow-up limit     |
| Repeated failure                    | Stop retrying           | Escalation rule     |

---

# 🛡️ Financial Safety Architecture

One of RecoverAI's most important design decisions is that **the LLM cannot directly execute financial actions**.

### Unsafe Architecture

```text
LLM
 ↓
"Give 20% discount"
 ↓
Payment API
```

### RecoverAI Architecture

```text
LLM
 ↓
"Recommend 20% discount"
 ↓
Policy Engine
 ↓
❌ Rejected
 ↓
Audit Log
```

Or:

```text
LLM
 ↓
"Recommend 5% discount"
 ↓
Policy Engine
 ↓
✅ Approved
 ↓
State Machine
 ↓
Payment Provider
```

This prevents AI hallucinations from becoming financial transactions.

---

# ⚙️ Deterministic Policy Engine

The policy engine acts as the **financial safety boundary**.

Example policies:

```text
MAX_RETRIES = 3

MAX_DISCOUNT = 5%

HIGH_VALUE_THRESHOLD = ₹1,00,000

MAX_RECOVERY_ATTEMPTS_PER_DAY = configurable

HUMAN_APPROVAL_REQUIRED = true
```

### Example Decision

```json
{
  "requested_action": "discount",
  "requested_discount": 10,
  "policy_limit": 5,
  "decision": "REJECTED",
  "reason": "Discount exceeds configured financial policy"
}
```

The AI can recommend an action.

The policy engine determines whether that action is **allowed**.

---

# 🔐 Idempotent Event Processing

Payment systems can deliver the same webhook multiple times.

RecoverAI prevents duplicate processing using deterministic event fingerprints.

```text
Incoming Webhook
       ↓
Normalize Payload
       ↓
SHA-256 Hash
       ↓
Check Existing Event
       ↓
 ┌─────┴─────┐
 │           │
Exists     New Event
 │           │
Skip        Process
             ↓
          Store Hash
```

This prevents:

* Duplicate recovery attempts
* Duplicate ledger entries
* Duplicate notifications
* Incorrect recovery metrics

---

# 🔄 Recovery State Machine

Every recovery opportunity follows a controlled lifecycle.

```mermaid
stateDiagram-v2

    [*] --> DETECTED

    DETECTED --> DIAGNOSED

    DIAGNOSED --> POLICY_CHECK

    POLICY_CHECK --> EXECUTING: Approved

    POLICY_CHECK --> ESCALATED: Approval Required

    POLICY_CHECK --> FAILED: Rejected

    EXECUTING --> RECOVERED: Payment Confirmed

    EXECUTING --> FAILED: Payment Failed

    FAILED --> DIAGNOSED: Retry Allowed

    FAILED --> ESCALATED: Retry Limit Reached

    ESCALATED --> EXECUTING: Human Approved

    RECOVERED --> [*]
```

Invalid state transitions are rejected at the application layer.

---

# 💰 Verified Revenue Recovery

RecoverAI distinguishes between:

### Potential Recovery

Money that the AI predicts could potentially be recovered.

### Attempted Recovery

Money associated with an executed recovery attempt.

### Verified Recovery

Money confirmed by the payment provider and reconciled in the ledger.

Only **verified recovery** contributes to the final recovered revenue metric.

```text
Potential Revenue
       ↓
AI Estimated Recovery
       ↓
Recovery Attempt
       ↓
Payment Confirmation
       ↓
Ledger Reconciliation
       ↓
Verified Recovered Revenue
```

This prevents the dashboard from reporting AI-generated or estimated numbers as real revenue.

---

# 📊 Command Center

The frontend acts as a **Revenue Operations Command Center**.

### Key dashboard metrics

* Total at-risk revenue
* Recoverable revenue
* Verified recovered revenue
* Recovery rate
* Recovery attempts
* Failed recoveries
* Policy rejections
* Human approvals
* Revenue by failure reason
* Revenue by recovery strategy
* Recovery funnel
* Recent recovery events

### Recovery Funnel

```text
At-Risk Revenue
       ↓
Diagnosed
       ↓
Eligible
       ↓
Recovery Attempted
       ↓
Payment Confirmed
       ↓
Revenue Recovered
```

---

# 🧪 Synthetic Revenue Simulator

RecoverAI includes a synthetic transaction simulator for demonstrating the platform without requiring production payment data.

The simulator can generate scenarios such as:

```text
✓ Card Failure
✓ Insufficient Funds
✓ Authentication Failure
✓ Checkout Abandonment
✓ Delayed Payment
✓ Customer Promise-to-Pay
✓ High-Value Transaction
✓ Repeated Failure
✓ Successful Recovery
✓ Failed Recovery
```

This allows the complete recovery pipeline to be demonstrated locally.

---

# 🏗️ Technology Stack

| Layer            | Technology                     |
| ---------------- | ------------------------------ |
| Frontend         | Next.js 14+, React, TypeScript |
| Styling          | Tailwind CSS                   |
| Visualization    | Recharts                       |
| Backend          | FastAPI                        |
| Language         | Python 3.11+                   |
| Validation       | Pydantic v2                    |
| ORM              | SQLAlchemy 2.0                 |
| Database         | PostgreSQL                     |
| AI Orchestration | LangGraph                      |
| LLM              | Configurable LLM Provider      |
| API              | REST + Webhooks + SSE          |
| Testing          | Pytest                         |
| Containers       | Docker + Docker Compose        |
| Version Control  | Git + GitHub                   |

---

# 📁 Repository Structure

```text
razpay_ai/
│
├── apps/
│   │
│   ├── web/
│   │   ├── app/
│   │   ├── components/
│   │   ├── lib/
│   │   ├── hooks/
│   │   └── public/
│   │
│   └── api/
│       ├── app/
│       │   ├── api/
│       │   ├── agents/
│       │   ├── domain/
│       │   ├── models/
│       │   ├── services/
│       │   ├── policies/
│       │   ├── state_machine/
│       │   └── main.py
│       │
│       ├── tests/
│       └── requirements.txt
│
├── simulator/
│   ├── scenarios/
│   ├── generators/
│   └── benchmark.py
│
├── docs/
│   ├── architecture/
│   ├── decisions/
│   └── api/
│
├── docker/
│   ├── api.Dockerfile
│   └── web.Dockerfile
│
├── docker-compose.yml
├── .env.example
├── .gitignore
├── LICENSE
└── README.md
```

---

# 🚀 Quick Start

## Prerequisites

Make sure you have:

* Python 3.11+
* Node.js 20+
* npm
* PostgreSQL
* Docker & Docker Compose *(recommended)*

---

## 1. Clone

```bash
git clone https://github.com/jayraj175coder/razpay_ai.git

cd razpay_ai
```

---

## 2. Configure Environment

```bash
cp .env.example .env
```

Configure the required environment variables.

```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/recoverai

LLM_API_KEY=your_api_key

PAYMENT_PROVIDER_MODE=mock

MAX_RETRIES=3

MAX_DISCOUNT_PERCENT=5

HIGH_VALUE_THRESHOLD=100000
```

Never commit `.env`.

---

# 🐳 Docker Setup

The recommended development setup is Docker Compose.

```bash
docker compose up --build
```

The stack starts the required services for local development.

---

# 💻 Manual Backend Setup

```bash
cd apps/api

python -m venv .venv
```

### Windows

```bash
.venv\Scripts\activate
```

### Linux / macOS

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Start the API:

```bash
uvicorn app.main:app --reload --port 8000
```

---

# 🌐 Manual Frontend Setup

```bash
cd apps/web

npm install

npm run dev
```

Open:

```text
http://localhost:3000
```

Backend:

```text
http://localhost:8000
```

API documentation:

```text
http://localhost:8000/docs
```

---

# 🧪 Testing

Run backend tests:

```bash
cd apps/api

pytest -v
```

Run frontend checks:

```bash
cd apps/web

npm run lint
```

Build production frontend:

```bash
npm run build
```

---

# 📈 Example Recovery Scenario

Consider a ₹75,000 payment failure.

```text
Payment
₹75,000
   ↓
FAILED
   ↓
Risk Engine
High Recovery Probability
   ↓
AI Diagnosis
Temporary payment failure
   ↓
AI Recommendation
Retry after cooldown
   ↓
Policy Engine
Retry count < 3
   ↓
✅ APPROVED
   ↓
Recovery Attempt
   ↓
Payment Successful
   ↓
Ledger Reconciliation
   ↓
₹75,000 VERIFIED RECOVERED
```

The dashboard then updates:

```text
At-Risk Revenue      ₹75,000
Recovery Attempted   ₹75,000
Verified Recovered   ₹75,000
Recovery Status      SUCCESS
```

---

# 🧠 Why RecoverAI Is Different

Most payment-recovery demos stop at:

```text
Payment Failed → Retry
```

RecoverAI builds a complete **decision + execution + verification loop**:

```text
Detect
  ↓
Understand
  ↓
Predict
  ↓
Decide
  ↓
Validate
  ↓
Execute
  ↓
Verify
  ↓
Learn
```

### Key differentiators

**1. Agentic reasoning**

The system doesn't rely on a single prompt. LangGraph coordinates multiple reasoning stages.

**2. AI safety boundary**

The LLM never directly controls financial execution.

**3. Policy enforcement**

Every AI recommendation passes through deterministic business rules.

**4. Verified financial metrics**

Revenue is counted only after provider confirmation and ledger reconciliation.

**5. Idempotent payments infrastructure**

Duplicate webhook events cannot create duplicate financial actions.

**6. Human-in-the-loop**

High-value or sensitive recovery actions can require explicit approval.

**7. Explainability**

Every recovery decision records:

```text
Why was this transaction selected?
Why was this strategy selected?
Which policy allowed/rejected it?
What action was executed?
What was the outcome?
How much revenue was actually recovered?
```

---

# 🔒 Production Readiness Principles

RecoverAI follows several principles expected in real payment infrastructure.

### Reliability

* Idempotent webhook processing
* Validated state transitions
* Transaction-safe ledger updates
* Retry boundaries

### Security

* Environment-based secrets
* Input validation
* API authentication-ready architecture
* No secrets committed to Git
* Financial action authorization boundaries

### Observability

* Structured event records
* Recovery audit trail
* State transition tracking
* Policy decisions
* Recovery metrics

### AI Safety

* AI recommendations are not automatically trusted
* Deterministic policy enforcement
* Bounded actions
* Human approval for sensitive operations
* No LLM-generated financial truth

---

# 🧩 Engineering Design Principle

The most important architectural principle of RecoverAI is:

```text
             ┌───────────────────────┐
             │        AI Layer       │
             │                       │
             │ "What should we do?"  │
             └───────────┬───────────┘
                         │
                         ▼
             ┌───────────────────────┐
             │   Policy Layer        │
             │                       │
             │ "Are we allowed?"     │
             └───────────┬───────────┘
                         │
                         ▼
             ┌───────────────────────┐
             │ Execution Layer       │
             │                       │
             │ "Do it safely."       │
             └───────────┬───────────┘
                         │
                         ▼
             ┌───────────────────────┐
             │ Ledger Layer          │
             │                       │
             │ "Did it really work?" │
             └───────────────────────┘
```

This creates a clean separation between:

> **Reasoning → Authorization → Execution → Verification**

---

# 🛣️ Roadmap

### Phase 1 — Foundation

* [x] Monorepo setup
* [x] Next.js frontend
* [x] FastAPI backend
* [x] PostgreSQL integration
* [x] Docker setup

### Phase 2 — Recovery Intelligence

* [x] Payment event ingestion
* [x] Revenue risk scoring
* [x] Recovery opportunity detection
* [x] LangGraph workflow
* [x] Strategy generation

### Phase 3 — Financial Safety

* [x] Policy engine
* [x] Retry limits
* [x] Discount limits
* [x] Human approval gates
* [x] State machine
* [x] Idempotency

### Phase 4 — Verification

* [x] Payment simulator
* [x] Webhook processing
* [x] Recovery ledger
* [x] Reconciliation
* [x] Audit trail

### Phase 5 — Command Center

* [x] Revenue dashboard
* [x] Recovery funnel
* [x] Strategy analytics
* [x] Event timeline
* [x] Recovery performance metrics

### Future

* [ ] Production Razorpay integration
* [ ] WhatsApp/SMS recovery channels
* [ ] Advanced customer segmentation
* [ ] Recovery strategy experimentation
* [ ] Offline evaluation benchmarks
* [ ] Model performance monitoring
* [ ] Multi-tenant architecture
* [ ] Role-based access control

---

# 📊 Evaluation Framework

RecoverAI can be evaluated using measurable business metrics.

| Metric                | Definition                                              |
| --------------------- | ------------------------------------------------------- |
| Recovery Rate         | Verified recovered transactions / eligible transactions |
| Recovered Revenue     | Provider-confirmed recovered amount                     |
| Attempt Success Rate  | Successful recovery attempts / total attempts           |
| Policy Rejection Rate | Rejected AI actions / proposed actions                  |
| Duplicate Prevention  | Duplicate events safely ignored                         |
| AI Decision Accuracy  | Correct diagnosis / evaluated cases                     |
| Recovery Latency      | Time from detection to successful recovery              |

The objective is not simply:

> **Generate more retries.**

The objective is:

> **Maximize verified recovered revenue while minimizing unnecessary customer interventions and financial risk.**

---

# 🏆 Challenge Alignment

**Razorpay AI Builder Challenge — Track 03: AI Revenue Recovery**

RecoverAI directly addresses the challenge by combining:

```text
Payment Intelligence
        +
Agentic AI
        +
Revenue Risk Detection
        +
Recovery Automation
        +
Financial Policy Enforcement
        +
Verified Revenue Measurement
```

The result is a complete revenue recovery system rather than a simple AI chatbot or payment retry script.

---

# 👨‍💻 Author

**Jayraj Sanas**

Computer Engineering Student
Mumbai, India

GitHub: `https://github.com/jayraj175coder`

---

# 📄 License

This project is licensed under the MIT License.

---

## ⭐ Final Architecture Summary

```text
                     RECOVERAI
                         │
                         ▼
                ┌─────────────────┐
                │ Payment Events  │
                └────────┬────────┘
                         ↓
                ┌─────────────────┐
                │ Risk Detection  │
                └────────┬────────┘
                         ↓
                ┌─────────────────┐
                │ AI Diagnosis    │
                │ + Intent        │
                └────────┬────────┘
                         ↓
                ┌─────────────────┐
                │ Strategy        │
                │ Recommendation  │
                └────────┬────────┘
                         ↓
                ┌─────────────────┐
                │ POLICY ENGINE   │
                │   🔒 SAFETY     │
                └────────┬────────┘
                         ↓
                ┌─────────────────┐
                │ STATE MACHINE   │
                └────────┬────────┘
                         ↓
                ┌─────────────────┐
                │ PAYMENT         │
                │ EXECUTION       │
                └────────┬────────┘
                         ↓
                ┌─────────────────┐
                │ RECONCILIATION  │
                └────────┬────────┘
                         ↓
                ┌─────────────────┐
                │ VERIFIED        │
                │ RECOVERED       │
                │ REVENUE         │
                └────────┬────────┘
                         ↓
                ┌─────────────────┐
                │ COMMAND CENTER  │
                └─────────────────┘
```

> **RecoverAI doesn't just predict lost revenue. It closes the loop from detection to verified recovery.**
