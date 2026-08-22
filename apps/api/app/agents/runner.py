"""Runner service for invoking LangGraph Recovery Agent."""
from typing import Any, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from app.agents.graph import RecoveryAgentGraph
from app.core.logging import get_logger

logger = get_logger("recoverai.agents.runner")


class RecoveryAgentRunner:
    """Entry point for executing agent workflows on cases."""

    @classmethod
    async def process_case(cls, session: AsyncSession, case_id: str) -> Dict[str, Any]:
        """Run complete LangGraph recovery pipeline on a case."""
        logger.info(f"Triggering LangGraph Recovery Agent for case_id={case_id}")
        graph = RecoveryAgentGraph(session)
        result_state = await graph.run(case_id)
        logger.info(f"Completed LangGraph Recovery Agent for case_id={case_id} -> final_status={result_state.get('final_status')}")
        return result_state
