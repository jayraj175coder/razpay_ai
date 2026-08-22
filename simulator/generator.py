"""Deterministic Synthetic Transaction and Recovery Case Generator."""
import random
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import List, Optional


@dataclass
class SyntheticTransaction:
    id: str
    customer_id: str
    customer_name: str
    customer_email: str
    customer_segment: str
    customer_ltv: float
    amount: float
    currency: str
    source_type: str
    failure_code: str
    failure_message: str
    past_successful_payments: int
    is_fraud: bool
    created_at: datetime


CUSTOMER_COMPANIES = [
    ("Nexus Cloud Technologies Pvt Ltd", "ENTERPRISE", 1850000.0),
    ("Zenscale Logistics India", "SMB", 320000.0),
    ("Kaveri Retail Ventures", "VIP", 680000.0),
    ("Bharat Finserve Solutions", "ENTERPRISE", 2400000.0),
    ("Indus Health Diagnostics", "SMB", 410000.0),
    ("Surya Solar Systems LLP", "SMB", 190000.0),
    ("Paramount SaaS Labs", "VIP", 890000.0),
    ("Urban Kart Logistics", "RETAIL", 45000.0),
    ("AeroTech Logistics Pune", "ENTERPRISE", 1450000.0),
    ("FreshGrocers Direct", "RETAIL", 28000.0),
]

FAILURE_TAXONOMY = [
    # (failure_code, source_type, avg_amount, failure_message, is_fraud, weight)
    ("network_timeout", "SUBSCRIPTION_DUNNING", 18500.0, "Interbank switch timeout during debit", False, 30),
    ("insufficient_funds", "PAYMENT_FAILURE", 35000.0, "Temporary insufficient funds in account", False, 25),
    ("card_expired", "PAYMENT_FAILURE", 14000.0, "Card validity expired MM/YY", False, 20),
    ("checkout_abandoned", "CHECKOUT_ABANDONMENT", 4999.0, "User dropped off at OTP checkout step", False, 15),
    ("insufficient_funds", "OVERDUE_INVOICE", 150000.0, "Corporate invoice past 30 days credit term", False, 8),
    ("fraud_suspected", "PAYMENT_FAILURE", 8500.0, "Stolen card velocity trigger", True, 2),
]


class SyntheticTransactionGenerator:
    """Generates realistic, seed-deterministic batches of revenue-at-risk transactions."""

    @classmethod
    def generate_batch(cls, count: int = 100, seed: int = 42) -> List[SyntheticTransaction]:
        rng = random.Random(seed)
        transactions: List[SyntheticTransaction] = []

        codes, source_types, avg_amounts, msgs, frauds, weights = zip(*FAILURE_TAXONOMY)

        for i in range(count):
            comp_name, segment, ltv = rng.choice(CUSTOMER_COMPANIES)
            cust_id = f"cust_sim_{uuid.UUID(int=rng.getrandbits(128)).hex[:8]}"
            cust_email = f"finance@{comp_name.lower().replace(' ', '').replace('pvtltd', '').replace('llp', '')}.in"

            # Pick failure profile weighted
            idx = rng.choices(range(len(FAILURE_TAXONOMY)), weights=weights, k=1)[0]
            code = codes[idx]
            source_type = source_types[idx]
            base_amt = avg_amounts[idx]
            msg = msgs[idx]
            is_fraud = frauds[idx]

            # Jitter amount by +/- 30%
            jitter = rng.uniform(0.7, 1.3)
            amount = round(base_amt * jitter, -1)  # Round to nearest 10
            if amount < 500:
                amount = 500.0

            past_success = rng.randint(2, 25) if segment in ["ENTERPRISE", "VIP"] else rng.randint(0, 10)

            txn = SyntheticTransaction(
                id=f"TXN-SIM-{i+1:04d}",
                customer_id=cust_id,
                customer_name=comp_name if segment != "RETAIL" else f"Retail Customer #{i+1}",
                customer_email=cust_email,
                customer_segment=segment,
                customer_ltv=ltv,
                amount=amount,
                currency="INR",
                source_type=source_type,
                failure_code=code,
                failure_message=msg,
                past_successful_payments=past_success,
                is_fraud=is_fraud,
                created_at=datetime.now(timezone.utc) - timedelta(hours=rng.randint(1, 72)),
            )
            transactions.append(txn)

        return transactions
