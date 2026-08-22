"""LangGraph Workflow Graph for AI Revenue Recovery."""
from typing import Any, Dict, Optional, TypedDict
from langgraph.graph import StateGraph, END
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.logging import get_logger
from app.models import (
    Customer,
    RecoveryCase,
    RecoveryAction,
    RecoveryAttempt,
    RecoveryPolicy,
    PolicyDecision,
    ActionExecutionStatus,
    RecoveryState,
    ActorType,
    AuditLog,
)
from app.agents.llm_client import llm_client
from app.agents.schemas import DiagnosisOutput, StrategyOutput
from app.agents.tools import AgentTools
from app.risk.engine import RevenueRiskEngine
from app.policies.engine import PolicyEngine
from app.state_machine.machine import RecoveryStateMachine
from app.providers.factory import get_payment_provider

logger = get_logger("recoverai.agents.graph")


class RecoveryAgentState(TypedDict):
    """Internal state carried through the LangGraph workflow."""
    case_id: str
    case: Optional[Dict[str, Any]]
    customer: Optional[Dict[str, Any]]
    diagnosis: Optional[Dict[str, Any]]
    risk_score: Optional[Dict[str, Any]]
    strategy: Optional[Dict[str, Any]]
    policy_evaluation: Optional[Dict[str, Any]]
    execution_result: Optional[Dict[str, Any]]
    final_status: Optional[str]
    audit_events: list[Dict[str, Any]]


class RecoveryAgentGraph:
    """Orchestrates the multi-stage AI reasoning & deterministic policy validation graph."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.workflow = self._build_graph()

    def _build_graph(self):
        graph = StateGraph(RecoveryAgentState)

        # Register nodes
        graph.add_node("load_case", self._node_load_case)
        graph.add_node("load_customer_context", self._node_load_customer_context)
        graph.add_node("diagnose", self._node_diagnose)
        graph.add_node("calculate_recovery_score", self._node_calculate_recovery_score)
        graph.add_node("select_strategy", self._node_select_strategy)
        graph.add_node("policy_check", self._node_policy_check)
        graph.add_node("execute_or_escalate", self._node_execute_or_escalate)
        graph.add_node("verify_result", self._node_verify_result)
        graph.add_node("update_recovery_ledger", self._node_update_recovery_ledger)
        graph.add_node("write_audit_log", self._node_write_audit_log)

        # Wire linear and conditional edges
        graph.set_entry_point("load_case")
        graph.add_edge("load_case", "load_customer_context")
        graph.add_edge("load_customer_context", "diagnose")
        graph.add_edge("diagnose", "calculate_recovery_score")
        graph.add_edge("calculate_recovery_score", "select_strategy")
        graph.add_edge("select_strategy", "policy_check")
        graph.add_edge("policy_check", "execute_or_escalate")
        graph.add_edge("execute_or_escalate", "verify_result")
        graph.add_edge("verify_result", "update_recovery_ledger")
        graph.add_edge("update_recovery_ledger", "write_audit_log")
        graph.add_edge("write_audit_log", END)

        return graph.compile()

    async def run(self, case_id: str) -> RecoveryAgentState:
        """Execute the LangGraph workflow for a recovery case."""
        initial_state: RecoveryAgentState = {
            "case_id": case_id,
            "case": None,
            "customer": None,
            "diagnosis": None,
            "risk_score": None,
            "strategy": None,
            "policy_evaluation": None,
            "execution_result": None,
            "final_status": None,
            "audit_events": [],
        }
        return await self.workflow.ainvoke(initial_state)

    async def _node_load_case(self, state: RecoveryAgentState) -> Dict[str, Any]:
        """Node 1: Load Case from database."""
        stmt = select(RecoveryCase).where(RecoveryCase.id == state["case_id"])
        res = await self.session.execute(stmt)
        case_obj = res.scalars().first()
        if not case_obj:
            raise ValueError(f"Recovery case {state['case_id']} not found")

        return {
            "case": {
                "id": case_obj.id,
                "customer_id": case_obj.customer_id,
                "amount_at_risk": case_obj.amount_at_risk,
                "currency": case_obj.currency,
                "source_type": case_obj.source_type.value,
                "source_id": case_obj.source_id,
                "failure_code": case_obj.root_cause or "insufficient_funds",
                "status": case_obj.status.value,
                "recovered_amount": case_obj.recovered_amount,
            }
        }

    async def _node_load_customer_context(self, state: RecoveryAgentState) -> Dict[str, Any]:
        """Node 2: Fetch Customer Context & History."""
        cust_id = state["case"]["customer_id"]
        customer_data = await AgentTools.get_customer_history(self.session, cust_id)
        return {"customer": customer_data or {}}

    async def _node_diagnose(self, state: RecoveryAgentState) -> Dict[str, Any]:
        """Node 3: AI Root-Cause Reasoning."""
        context = {
            "failure_code": state["case"]["failure_code"],
            "amount": state["case"]["amount_at_risk"],
            "customer_name": state["customer"].get("name", "Customer"),
            "source_type": state["case"]["source_type"],
            "lifetime_value": state["customer"].get("lifetime_value", 0.0),
        }
        prompt = (
            f"Diagnose failure for {context['customer_name']}. "
            f"Failure code: '{context['failure_code']}', Amount: INR {context['amount']:.2f}, "
            f"LTV: INR {context['lifetime_value']:.2f}, Source: {context['source_type']}."
        )
        system_prompt = "You are an expert fintech risk diagnostician. Determine the root cause of payment failure."
        diagnosis = await llm_client.generate_structured(prompt, system_prompt, DiagnosisOutput, context)
        return {"diagnosis": diagnosis.model_dump()}

    async def _node_calculate_recovery_score(self, state: RecoveryAgentState) -> Dict[str, Any]:
        """Node 4: Deterministic Risk & Recovery Probability Scoring."""
        risk_result = RevenueRiskEngine.assess_risk(
            amount=state["case"]["amount_at_risk"],
            failure_code=state["diagnosis"]["root_cause"],
            customer_segment=state["customer"].get("segment", "RETAIL"),
            lifetime_value=state["customer"].get("lifetime_value", 0.0),
            past_successful_payments=5,
        )
        return {"risk_score": risk_result.to_dict()}

    async def _node_select_strategy(self, state: RecoveryAgentState) -> Dict[str, Any]:
        """Node 5: AI Strategy Selection."""
        context = {
            "failure_code": state["diagnosis"]["root_cause"],
            "amount": state["case"]["amount_at_risk"],
            "customer_name": state["customer"].get("name", "Customer"),
            "source_type": state["case"]["source_type"],
            "recovery_prob": state["risk_score"]["recovery_probability"],
            "priority": state["risk_score"]["priority_score"],
        }
        prompt = (
            f"Select recovery strategy for customer {context['customer_name']}. "
            f"Diagnosed cause: '{context['failure_code']}', Amount: INR {context['amount']:.2f}, "
            f"Priority Score: {context['priority']:.1f}, Recovery Probability: {context['recovery_prob']:.2f}."
        )
        system_prompt = "You are an AI recovery strategist. Select the safest bounded recovery action."
        strategy = await llm_client.generate_structured(prompt, system_prompt, StrategyOutput, context)
        return {"strategy": strategy.model_dump()}

    async def _node_policy_check(self, state: RecoveryAgentState) -> Dict[str, Any]:
        """Node 6: Deterministic Policy Engine Gate."""
        policy = await AgentTools.get_active_policy(self.session)
        policy_eval = PolicyEngine.evaluate(
            policy=policy,
            action_type=state["strategy"]["recommended_action"],
            amount_at_risk=state["case"]["amount_at_risk"],
            failure_code=state["diagnosis"]["root_cause"],
            attempts_count=0,
            messages_sent=0,
            proposed_discount_pct=state["strategy"].get("proposed_discount_pct", 0.0),
        )
        return {"policy_evaluation": policy_eval.to_dict()}

    async def _node_execute_or_escalate(self, state: RecoveryAgentState) -> Dict[str, Any]:
        """Node 7: Bounded Action Execution or Escalation."""
        policy_eval = state["policy_evaluation"]
        strategy = state["strategy"]
        case_data = state["case"]

        if policy_eval["decision"] == PolicyDecision.REQUIRES_HUMAN_APPROVAL.value:
            return {
                "execution_result": {"status": "escalated", "action": strategy["recommended_action"], "reason": policy_eval["reason"]},
                "final_status": RecoveryState.ESCALATED.value,
            }
        elif policy_eval["decision"] == PolicyDecision.BLOCKED.value:
            return {
                "execution_result": {"status": "blocked", "action": strategy["recommended_action"], "reason": policy_eval["reason"]},
                "final_status": RecoveryState.STOPPED.value,
            }
        else:
            # Policy ALLOWED: Execute via Provider
            action_type = strategy["recommended_action"]
            if action_type == "RETRY_PAYMENT":
                res = await AgentTools.execute_retry_payment(
                    transaction_id=case_data["source_id"],
                    amount=case_data["amount_at_risk"],
                    currency=case_data["currency"],
                )
                return {"execution_result": res, "final_status": RecoveryState.AWAITING_RESULT.value}
            elif action_type in ["CREATE_PAYMENT_LINK", "SEND_PAYMENT_REMINDER"]:
                link_res = await AgentTools.create_payment_link(
                    customer_id=case_data["customer_id"],
                    amount=case_data["amount_at_risk"],
                    description=f"RecoverAI Payment Link for {case_data['id']}",
                )
                return {"execution_result": link_res, "final_status": RecoveryState.EXECUTING.value}
            else:
                return {
                    "execution_result": {"status": "scheduled", "action": action_type},
                    "final_status": RecoveryState.EXECUTING.value,
                }

    async def _node_verify_result(self, state: RecoveryAgentState) -> Dict[str, Any]:
        """Node 8: Verify Outcome & Ledger updates."""
        exec_res = state["execution_result"] or {}
        if exec_res.get("success") is True and state["strategy"]["recommended_action"] == "RETRY_PAYMENT":
            return {"final_status": RecoveryState.RECOVERED.value}
        return {}

    async def _node_update_recovery_ledger(self, state: RecoveryAgentState) -> Dict[str, Any]:
        """Node 9: Persist updates to DB RecoveryCase and Actions."""
        stmt = select(RecoveryCase).where(RecoveryCase.id == state["case_id"])
        res = await self.session.execute(stmt)
        case_obj = res.scalars().first()

        if case_obj:
            case_obj.root_cause = state["diagnosis"]["root_cause"]
            case_obj.root_cause_explanation = state["diagnosis"]["explanation"]
            case_obj.recommended_action = state["strategy"]["recommended_action"]
            case_obj.recommended_channel = state["strategy"]["recommended_channel"]
            case_obj.ai_reasoning = state["strategy"]["reasoning"]
            case_obj.recovery_probability = state["risk_score"]["recovery_probability"]
            case_obj.priority_score = state["risk_score"]["priority_score"]
            case_obj.risk_category = state["risk_score"]["risk_category"]
            case_obj.signals_json = {
                "positive": state["risk_score"]["positive_signals"],
                "negative": state["risk_score"]["negative_signals"],
            }

            final_st = state.get("final_status") or RecoveryState.EXECUTING.value
            case_obj.status = RecoveryState(final_st)
            if case_obj.status == RecoveryState.RECOVERED:
                case_obj.recovered_amount = case_obj.amount_at_risk

            # Record RecoveryAction
            action_rec = RecoveryAction(
                recovery_case_id=case_obj.id,
                action_type=state["strategy"]["recommended_action"],
                action_reason=state["strategy"]["reasoning"],
                policy_decision=state["policy_evaluation"]["decision"],
                policy_reason=state["policy_evaluation"]["reason"],
                status=(
                    ActionExecutionStatus.EXECUTED
                    if state["policy_evaluation"]["allowed"]
                    else ActionExecutionStatus.BLOCKED
                ),
                payload_json=state["strategy"],
                result_json=state["execution_result"],
            )
            self.session.add(action_rec)
            await self.session.flush()

        return {}

    async def _node_write_audit_log(self, state: RecoveryAgentState) -> Dict[str, Any]:
        """Node 10: Commit immutable AuditLog entries."""
        case_id = state["case_id"]
        
        # Log AI Diagnosis
        audit_diag = AuditLog(
            case_id=case_id,
            actor_type=ActorType.AI_AGENT,
            actor_id="langgraph_recovery_agent",
            action="AI_DIAGNOSIS_AND_STRATEGY_GENERATED",
            reason=state["strategy"]["reasoning"],
            metadata_json={
                "root_cause": state["diagnosis"]["root_cause"],
                "confidence": state["diagnosis"]["confidence"],
                "action": state["strategy"]["recommended_action"],
            },
        )
        self.session.add(audit_diag)

        # Log Policy Gate
        audit_policy = AuditLog(
            case_id=case_id,
            actor_type=ActorType.POLICY_ENGINE,
            actor_id="policy_engine_v1",
            action="POLICY_DECISION_RECORDED",
            reason=state["policy_evaluation"]["reason"],
            metadata_json=state["policy_evaluation"],
        )
        self.session.add(audit_policy)

        await self.session.commit()
        return {}
