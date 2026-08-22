# RecoverAI — Production-Grade AI Revenue Recovery Platform

> **Detect revenue leakage. Decide the safest intervention. Recover the money. Prove the outcome.**

Built for the **Razorpay AI Builder Challenge — Track 03: AI Revenue Recovery**.

---

## 🏛️ System Architecture

RecoverAI cleanly separates **probabilistic AI reasoning** from **deterministic financial enforcement**:

```
                          ┌───────────────────────────┐
                          │   Next.js 14+ Frontend    │
                          │ (Command Center Dashboard)│
                          └─────────────┬─────────────┘
                                        │ REST / SSE
                                        ▼
                          ┌───────────────────────────┐
                          │     FastAPI Backend       │
                          │   (REST APIs & Webhooks)  │
                          └──────┬─────────────┬──────┘
                                 │             │
                    ┌────────────┴──┐       ┌──┴────────────┐
                    ▼               ▼       ▼               ▼
            ┌──────────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
            │ Revenue Risk │ │LangGraph │ │ Policy   │ │ State    │
            │ Engine       │ │AI Agent  │ │ Engine   │ │ Machine  │
            └──────────────┘ └──────────┘ └──────────┘ └──────────┘
                    │               │       │               │
                    └────────────┬──┘       └──┬────────────┘
                                 ▼             ▼
                          ┌───────────────────────────┐
                          │ Payment Provider Sandbox  │
                          │  (Mock / Razorpay-ready)  │
                          └─────────────┬─────────────┘
                                        ▼
                          ┌───────────────────────────┐
                          │  PostgreSQL / SQLAlchemy  │
                          │  (Recovery Ledger & Audit)│
                          └───────────────────────────┘
```

### Core Separation of Responsibilities

| Subsystem | Component | Responsibility |
|---|---|---|
| **Probabilistic AI** | LangGraph & LLM | Root-cause analysis, behavioral context interpretation, reminder copy synthesis, promise-to-pay extraction |
| **Deterministic Code** | Policy Engine | Max retry limits (3), frequency limits, discount caps (5%), human approval gates (> ₹1,00,000) |
| **Deterministic Code** | State Machine | Strict validated lifecycle: `DETECTED` → `DIAGNOSED` → `POLICY_CHECK` → `EXECUTING` → `RECOVERED` |
| **Deterministic Code** | Financial Ledger | Reconciled ledger calculating verified recovered revenue without hallucinated numbers |
| **Deterministic Code** | Idempotency | SHA-256 payload hashing preventing duplicate webhook event processing |

---

## 🚀 Quickstart

### Prerequisites
- Python 3.11+
- Node.js 20+
- Docker & Docker Compose (optional, for full containerized stack)

### 1. Environment Setup
```bash
cp .env.example .env
```

### 2. Backend Setup
```bash
cd apps/api
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 3. Frontend Setup
```bash
cd apps/web
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

---

## 🧪 Testing

```bash
# Run backend tests
cd apps/api
pytest -v
```

---

## 📦 Monorepo Structure

```text
razpay_ai/
├── apps/
│   ├── web/                     # Next.js 14+ Frontend (App Router, Tailwind, Recharts)
│   └── api/                     # FastAPI Backend (SQLAlchemy 2.0, Pydantic v2, LangGraph)
├── simulator/                   # Synthetic batch benchmark engine
├── docs/                        # Deep-dive architecture & decision records
├── docker/                      # Dockerfiles for API & Web
├── docker-compose.yml           # Multi-service local setup
├── .env.example
├── .gitignore
├── README.md
└── LICENSE
```
