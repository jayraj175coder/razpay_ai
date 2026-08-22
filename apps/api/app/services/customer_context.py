"""Real Customer Context Aggregation Service querying live database tables."""
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models import (
    Customer,
    CustomerSegment,
    Transaction,
    TransactionStatus,
    Payment,
    PaymentStatus,
    Subscription,
    SubscriptionStatus,
    Invoice,
    InvoiceStatus,
    RecoveryCase,
    RecoveryAttempt,
    RecoveryAction,
    PromiseToPay,
    PromiseStatus,
)

logger = get_logger("recoverai.services.customer_context")


@dataclass
class CustomerContext:
    customer_id: str
    name: str
    email: str
    phone: Optional[str]
    segment: CustomerSegment
    lifetime_value: float
    successful_payments_count: int
    failed_payments_count: int
    recent_failures: List[str] = field(default_factory=list)
    previous_recovery_cases_count: int = 0
    previous_recovery_attempts_count: int = 0
    recent_communications_count: int = 0  # in last 7 days
    active_subscriptions_count: int = 0
    overdue_invoices_count: int = 0
    total_overdue_invoice_amount: float = 0.0
    has_active_promise: bool = False
    fulfilled_promises_count: int = 0
    broken_promises_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "customer_id": self.customer_id,
            "name": self.name,
            "email": self.email,
            "phone": self.phone,
            "segment": self.segment.value if hasattr(self.segment, "value") else str(self.segment),
            "lifetime_value": self.lifetime_value,
            "successful_payments_count": self.successful_payments_count,
            "failed_payments_count": self.failed_payments_count,
            "recent_failures": self.recent_failures,
            "previous_recovery_cases_count": self.previous_recovery_cases_count,
            "previous_recovery_attempts_count": self.previous_recovery_attempts_count,
            "recent_communications_count": self.recent_communications_count,
            "active_subscriptions_count": self.active_subscriptions_count,
            "overdue_invoices_count": self.overdue_invoices_count,
            "total_overdue_invoice_amount": self.total_overdue_invoice_amount,
            "has_active_promise": self.has_active_promise,
            "fulfilled_promises_count": self.fulfilled_promises_count,
            "broken_promises_count": self.broken_promises_count,
        }


class CustomerContextService:
    """
    Aggregates comprehensive historical payment, subscription, invoice,
    and recovery data for a customer from live database records.
    """

    @classmethod
    async def load_customer_context(
        cls,
        session: AsyncSession,
        customer_id: str,
    ) -> CustomerContext:
        logger.info(f"Loading real customer context for customer_id='{customer_id}'")

        # 1. Load Customer profile
        stmt_cust = select(Customer).where(Customer.id == customer_id)
        res_cust = await session.execute(stmt_cust)
        customer = res_cust.scalars().first()

        if not customer:
            logger.warning(f"Customer '{customer_id}' not found in DB; returning default context")
            return CustomerContext(
                customer_id=customer_id,
                name="Unknown Customer",
                email="unknown@example.com",
                phone=None,
                segment=CustomerSegment.RETAIL,
                lifetime_value=0.0,
                successful_payments_count=0,
                failed_payments_count=0,
            )

        # 2. Transaction history counts
        stmt_success = select(func.count(Transaction.id)).where(
            Transaction.customer_id == customer_id,
            Transaction.status == TransactionStatus.SUCCESS,
        )
        success_cnt = (await session.execute(stmt_success)).scalar() or 0

        stmt_failed = select(func.count(Transaction.id)).where(
            Transaction.customer_id == customer_id,
            Transaction.status == TransactionStatus.FAILED,
        )
        failed_cnt = (await session.execute(stmt_failed)).scalar() or 0

        # Recent failure reasons
        stmt_recent_fail = (
            select(Transaction.failure_reason)
            .where(
                Transaction.customer_id == customer_id,
                Transaction.status == TransactionStatus.FAILED,
                Transaction.failure_reason.isnot(None),
            )
            .order_by(Transaction.created_at.desc())
            .limit(5)
        )
        recent_fails = [f for f in (await session.execute(stmt_recent_fail)).scalars().all() if f]

        # 3. Recovery case & attempt history
        stmt_cases = select(func.count(RecoveryCase.id)).where(RecoveryCase.customer_id == customer_id)
        cases_cnt = (await session.execute(stmt_cases)).scalar() or 0

        # Subquery for attempts through recovery cases
        stmt_case_ids = select(RecoveryCase.id).where(RecoveryCase.customer_id == customer_id)
        stmt_att_cnt = select(func.count(RecoveryAttempt.id)).where(RecoveryAttempt.recovery_case_id.in_(stmt_case_ids))
        att_cnt = (await session.execute(stmt_att_cnt)).scalar() or 0

        # 4. Recent communication actions (last 7 days)
        seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
        stmt_comm_cnt = (
            select(func.count(RecoveryAction.id))
            .join(RecoveryCase, RecoveryAction.recovery_case_id == RecoveryCase.id)
            .where(
                RecoveryCase.customer_id == customer_id,
                RecoveryAction.created_at >= seven_days_ago,
            )
        )
        comm_cnt = (await session.execute(stmt_comm_cnt)).scalar() or 0

        # 5. Subscriptions
        stmt_subs = select(func.count(Subscription.id)).where(
            Subscription.customer_id == customer_id,
            Subscription.status == SubscriptionStatus.ACTIVE,
        )
        subs_cnt = (await session.execute(stmt_subs)).scalar() or 0

        # 6. Invoices
        stmt_inv_cnt = select(func.count(Invoice.id)).where(
            Invoice.customer_id == customer_id,
            Invoice.status == InvoiceStatus.OVERDUE,
        )
        inv_cnt = (await session.execute(stmt_inv_cnt)).scalar() or 0

        stmt_inv_sum = select(func.coalesce(func.sum(Invoice.amount), 0.0)).where(
            Invoice.customer_id == customer_id,
            Invoice.status == InvoiceStatus.OVERDUE,
        )
        inv_sum = float((await session.execute(stmt_inv_sum)).scalar() or 0.0)

        # 7. Promises to Pay
        stmt_active_prom = select(func.count(PromiseToPay.id)).where(
            PromiseToPay.customer_id == customer_id,
            PromiseToPay.status.in_([PromiseStatus.PROMISED, PromiseStatus.WAITING]),
        )
        has_active_promise = ((await session.execute(stmt_active_prom)).scalar() or 0) > 0

        stmt_ful_prom = select(func.count(PromiseToPay.id)).where(
            PromiseToPay.customer_id == customer_id,
            PromiseToPay.status == PromiseStatus.FULFILLED,
        )
        ful_prom_cnt = (await session.execute(stmt_ful_prom)).scalar() or 0

        stmt_brk_prom = select(func.count(PromiseToPay.id)).where(
            PromiseToPay.customer_id == customer_id,
            PromiseToPay.status == PromiseStatus.BROKEN,
        )
        brk_prom_cnt = (await session.execute(stmt_brk_prom)).scalar() or 0

        return CustomerContext(
            customer_id=customer.id,
            name=customer.name,
            email=customer.email,
            phone=customer.phone,
            segment=customer.segment,
            lifetime_value=float(customer.lifetime_value or 0.0),
            successful_payments_count=success_cnt,
            failed_payments_count=failed_cnt,
            recent_failures=recent_fails,
            previous_recovery_cases_count=cases_cnt,
            previous_recovery_attempts_count=att_cnt,
            recent_communications_count=comm_cnt,
            active_subscriptions_count=subs_cnt,
            overdue_invoices_count=inv_cnt,
            total_overdue_invoice_amount=inv_sum,
            has_active_promise=has_active_promise,
            fulfilled_promises_count=ful_prom_cnt,
            broken_promises_count=brk_prom_cnt,
        )
