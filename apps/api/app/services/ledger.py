"""Financial Recovery Ledger and Analytics Service."""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import func, select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    Customer,
    RecoveryCase,
    RecoveryAction,
    RecoveryAttempt,
    RecoveryState,
    RecoverySourceType,
    PolicyDecision,
    ActionExecutionStatus,
    AuditLog,
    PromiseToPay,
)


class LedgerService:
    """Calculates financial metrics directly from immutable database ledger records."""

    @classmethod
    async def get_metrics(cls, session: AsyncSession) -> Dict[str, Any]:
        """Compute aggregated recovery metrics from database ledger."""
        # 1. Total revenue at risk
        stmt_risk = select(func.coalesce(func.sum(RecoveryCase.amount_at_risk), 0.0))
        res_risk = await session.execute(stmt_risk)
        total_at_risk = float(res_risk.scalar_one())

        # 2. Total recovered revenue
        stmt_recovered = select(func.coalesce(func.sum(RecoveryCase.recovered_amount), 0.0))
        res_recovered = await session.execute(stmt_recovered)
        total_recovered = float(res_recovered.scalar_one())

        # 3. Total recoverable (cases with probability >= 0.50 and not stopped)
        stmt_recoverable = select(
            func.coalesce(func.sum(RecoveryCase.amount_at_risk), 0.0)
        ).where(
            RecoveryCase.recovery_probability >= 0.50,
            RecoveryCase.status != RecoveryState.STOPPED,
        )
        res_recoverable = await session.execute(stmt_recoverable)
        total_recoverable = float(res_recoverable.scalar_one())

        # 4. Recovery Rate
        recovery_rate = (total_recovered / total_at_risk * 100.0) if total_at_risk > 0 else 0.0

        # 5. Case state counts
        stmt_cases = select(RecoveryCase.status, func.count(RecoveryCase.id)).group_by(RecoveryCase.status)
        res_cases = await session.execute(stmt_cases)
        status_counts = {row[0].value: row[1] for row in res_cases.all()}

        active_cases = sum(
            count for st, count in status_counts.items()
            if st not in [RecoveryState.RECOVERED.value, RecoveryState.STOPPED.value]
        )
        total_cases = sum(status_counts.values())

        # 6. Action counts
        stmt_actions = select(RecoveryAction.policy_decision, func.count(RecoveryAction.id)).group_by(RecoveryAction.policy_decision)
        res_actions = await session.execute(stmt_actions)
        decision_counts = {row[0].value: row[1] for row in res_actions.all()}

        automated_actions = decision_counts.get(PolicyDecision.ALLOWED.value, 0)
        human_escalations = decision_counts.get(PolicyDecision.REQUIRES_HUMAN_APPROVAL.value, 0)
        policy_blocks = decision_counts.get(PolicyDecision.BLOCKED.value, 0)

        # 7. Breakdown by Source Type
        stmt_source = select(
            RecoveryCase.source_type,
            func.coalesce(func.sum(RecoveryCase.amount_at_risk), 0.0),
            func.coalesce(func.sum(RecoveryCase.recovered_amount), 0.0),
            func.count(RecoveryCase.id),
        ).group_by(RecoveryCase.source_type)
        res_source = await session.execute(stmt_source)
        source_breakdown = [
            {
                "source_type": row[0].value,
                "amount_at_risk": float(row[1]),
                "recovered_amount": float(row[2]),
                "case_count": int(row[3]),
                "recovery_rate": (float(row[2]) / float(row[1]) * 100.0) if float(row[1]) > 0 else 0.0,
            }
            for row in res_source.all()
        ]

        return {
            "total_revenue_at_risk": total_at_risk,
            "total_recoverable_revenue": total_recoverable,
            "total_recovered_revenue": total_recovered,
            "recovery_rate_pct": round(recovery_rate, 2),
            "active_cases_count": active_cases,
            "total_cases_count": total_cases,
            "status_counts": status_counts,
            "automated_actions_count": automated_actions,
            "human_escalations_count": human_escalations,
            "policy_blocked_actions_count": policy_blocks,
            "source_breakdown": source_breakdown,
            "calculated_at": datetime.now(timezone.utc).isoformat(),
        }

    @classmethod
    async def list_cases(
        cls,
        session: AsyncSession,
        status: Optional[str] = None,
        source_type: Optional[str] = None,
        risk_category: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Query recovery cases with customer metadata."""
        query = select(RecoveryCase).options(selectinload(RecoveryCase.customer)).order_by(desc(RecoveryCase.priority_score))

        if status:
            query = query.where(RecoveryCase.status == RecoveryState(status))
        if source_type:
            query = query.where(RecoveryCase.source_type == RecoverySourceType(source_type))
        if risk_category:
            query = query.where(RecoveryCase.risk_category == risk_category)

        query = query.limit(limit).offset(offset)
        res = await session.execute(query)
        cases = res.scalars().all()

        results = []
        for c in cases:
            if search and search.lower() not in (c.id.lower() + " " + (c.customer.name if c.customer else "").lower()):
                continue
            results.append({
                "id": c.id,
                "source_type": c.source_type.value,
                "source_id": c.source_id,
                "customer_id": c.customer_id,
                "customer_name": c.customer.name if c.customer else "Unknown",
                "customer_segment": c.customer.segment.value if c.customer else "RETAIL",
                "amount_at_risk": c.amount_at_risk,
                "currency": c.currency,
                "recovery_probability": c.recovery_probability,
                "priority_score": c.priority_score,
                "risk_category": c.risk_category.value,
                "root_cause": c.root_cause,
                "recommended_action": c.recommended_action,
                "status": c.status.value,
                "recovered_amount": c.recovered_amount,
                "created_at": c.created_at.isoformat(),
                "updated_at": c.updated_at.isoformat(),
            })
        return results

    @classmethod
    async def get_case_detail(cls, session: AsyncSession, case_id: str) -> Optional[Dict[str, Any]]:
        """Fetch detailed investigation record for a recovery case."""
        stmt = (
            select(RecoveryCase)
            .where(RecoveryCase.id == case_id)
            .options(
                selectinload(RecoveryCase.customer),
                selectinload(RecoveryCase.actions),
                selectinload(RecoveryCase.attempts),
                selectinload(RecoveryCase.promises),
                selectinload(RecoveryCase.audit_logs),
            )
        )
        res = await session.execute(stmt)
        case = res.scalars().first()
        if not case:
            return None

        return {
            "id": case.id,
            "source_type": case.source_type.value,
            "source_id": case.source_id,
            "customer": {
                "id": case.customer.id,
                "name": case.customer.name,
                "email": case.customer.email,
                "phone": case.customer.phone,
                "segment": case.customer.segment.value,
                "lifetime_value": case.customer.lifetime_value,
            } if case.customer else None,
            "amount_at_risk": case.amount_at_risk,
            "currency": case.currency,
            "recovery_probability": case.recovery_probability,
            "priority_score": case.priority_score,
            "risk_category": case.risk_category.value,
            "root_cause": case.root_cause,
            "root_cause_explanation": case.root_cause_explanation,
            "recommended_action": case.recommended_action,
            "recommended_channel": case.recommended_channel,
            "ai_reasoning": case.ai_reasoning,
            "signals": case.signals_json or {},
            "status": case.status.value,
            "stopping_reason": case.stopping_reason,
            "recovered_amount": case.recovered_amount,
            "actions": [
                {
                    "id": a.id,
                    "action_type": a.action_type.value,
                    "action_reason": a.action_reason,
                    "policy_decision": a.policy_decision.value,
                    "policy_reason": a.policy_reason,
                    "status": a.status.value,
                    "payload": a.payload_json,
                    "result": a.result_json,
                    "created_at": a.created_at.isoformat(),
                }
                for a in case.actions
            ],
            "attempts": [
                {
                    "id": att.id,
                    "attempt_number": att.attempt_number,
                    "action_type": att.action_type,
                    "result": att.result,
                    "attempted_at": att.attempted_at.isoformat(),
                }
                for att in case.attempts
            ],
            "promises": [
                {
                    "id": p.id,
                    "promised_amount": p.promised_amount,
                    "promise_date": p.promise_date.isoformat(),
                    "confidence": p.confidence,
                    "raw_text": p.raw_text,
                    "status": p.status.value,
                }
                for p in case.promises
            ],
            "audit_logs": [
                {
                    "id": log.id,
                    "actor_type": log.actor_type.value,
                    "actor_id": log.actor_id,
                    "action": log.action,
                    "reason": log.reason,
                    "metadata": log.metadata_json,
                    "created_at": log.created_at.isoformat(),
                }
                for log in sorted(case.audit_logs, key=lambda x: x.created_at, reverse=True)
            ],
            "created_at": case.created_at.isoformat(),
            "updated_at": case.updated_at.isoformat(),
        }
