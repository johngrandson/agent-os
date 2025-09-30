"""Service for running accuracy evaluations using configured agents"""

import asyncio
from typing import Any

from agno.eval.accuracy import AccuracyEval
from app.domains.evaluation.events.publisher import EvaluationEventPublisher
from app.infrastructure.providers.agno.provider import AgnoDatabaseFactory, AgnoProvider
from app.shared.events.broker import broker
from core.logger import get_module_logger


logger = get_module_logger(__name__)


class AccuracyEvalService:
    """Service for running accuracy evaluations with configured agents"""

    def __init__(self, agent_provider: AgnoProvider):
        self.agent_provider = agent_provider
        self.db = AgnoDatabaseFactory.create_postgres_db()
        self.event_publisher = EvaluationEventPublisher(broker=broker)

    def _extract_eval_id(self, accuracy_eval: AccuracyEval) -> str:
        """
        Extract evaluation ID from AccuracyEval object.

        Args:
            accuracy_eval: The AccuracyEval object to extract ID from

        Returns:
            The eval_id if available, otherwise "unknown"
        """
        return accuracy_eval.eval_id if hasattr(accuracy_eval, "eval_id") else "unknown"

    def _extract_avg_score(self, result: Any) -> float:
        """
        Extract average score from evaluation result.

        Tries two approaches:
        1. Call compute_stats() if available and get avg_score from stats
        2. Fall back to direct avg_score attribute if present

        Args:
            result: The evaluation result object

        Returns:
            The average score as a float, or 0.0 if not found
        """
        if not result:
            return 0.0

        # Primary method: compute_stats()
        if hasattr(result, "compute_stats"):
            stats = result.compute_stats()
            if stats and isinstance(stats, dict):
                return stats.get("avg_score", 0.0)

        # Fallback: direct avg_score attribute (only if it's a real attribute, not Mock)
        if hasattr(result, "avg_score"):
            avg_score = result.avg_score
            # Ensure it's a number, not a Mock or other object
            if isinstance(avg_score, (int, float)):
                return float(avg_score)

        return 0.0

    async def _publish_failure_event_if_needed(
        self,
        status: str,
        eval_id: str,
        agent_id: str,
        eval_name: str,
        avg_score: float,
        input_text: str,
        expected_output: str,
        num_iterations: int,
    ) -> None:
        """
        Publish evaluation.failed event if evaluation failed with a known eval_id.

        Args:
            status: Evaluation status ("passed" or "failed")
            eval_id: Evaluation ID
            agent_id: Agent ID being evaluated
            eval_name: Name of the evaluation
            avg_score: Average score achieved
            input_text: Input used for evaluation
            expected_output: Expected output
            num_iterations: Number of iterations run
        """
        if status == "failed" and eval_id != "unknown":
            await self.event_publisher.eval_failed(
                agent_id=agent_id,
                eval_data={
                    "eval_id": eval_id,
                    "eval_name": eval_name,
                    "avg_score": avg_score,
                    "input": input_text,
                    "expected_output": expected_output,
                    "num_iterations": num_iterations,
                },
            )
            logger.info(f"Published evaluation.failed event for eval {eval_id}")

    async def run_accuracy_eval(
        self,
        agent_id: str,
        eval_name: str,
        input_text: str,
        expected_output: str,
        num_iterations: int = 1,
        additional_guidelines: str | None = None,
    ) -> dict[str, Any]:
        """
        Run accuracy evaluation using configured agent from AgnoProvider.

        This ensures the agent has all customizations:
        - KnowledgeTools with think/search/analyze
        - Custom instructions for language and knowledge base usage
        - Same database as AgentOS for persistence

        Args:
            agent_id: Agent ID to evaluate
            eval_name: Name for this evaluation run
            input_text: Input to send to agent
            expected_output: Expected response
            num_iterations: Number of times to run eval
            additional_guidelines: Optional additional evaluation guidelines

        Returns:
            Dictionary with evaluation results
        """
        logger.info(f"Running accuracy eval '{eval_name}' for agent {agent_id[:8]}")

        # Get configured agent from provider (await since it's async)
        # get_agent() returns the Agno Agent directly, not AgnoRuntimeAgent
        agno_agent = await self.agent_provider.get_agent(agent_id)
        if not agno_agent:
            raise ValueError(f"Agent {agent_id} not found in provider")

        # Create AccuracyEval with same db as AgentOS
        accuracy_eval = AccuracyEval(
            name=eval_name,
            agent=agno_agent,
            input=input_text,
            expected_output=expected_output,
            num_iterations=num_iterations,
            additional_guidelines=additional_guidelines,
            db=self.db,  # Use same db as AgentOS for persistence
        )

        # Run evaluation in thread pool (Agno's eval uses sync code)
        loop = asyncio.get_event_loop()

        def run_eval() -> Any:
            return accuracy_eval.run(print_results=False, print_summary=False)

        result = await loop.run_in_executor(None, run_eval)

        # Extract results using helper methods
        eval_id = self._extract_eval_id(accuracy_eval)
        avg_score = self._extract_avg_score(result)
        status = "passed" if avg_score >= 8.0 else "failed"

        logger.info(
            f"Eval '{eval_name}' completed: {avg_score:.2f}/10.0 ({status}) - ID: {eval_id}"
        )

        # Publish failure event if needed
        await self._publish_failure_event_if_needed(
            status=status,
            eval_id=eval_id,
            agent_id=agent_id,
            eval_name=eval_name,
            avg_score=avg_score,
            input_text=input_text,
            expected_output=expected_output,
            num_iterations=num_iterations,
        )

        return {
            "eval_id": eval_id,
            "agent_id": agent_id,
            "name": eval_name,
            "avg_score": avg_score,
            "num_iterations": num_iterations,
            "status": status,
            "message": f"Evaluation completed with average score {avg_score:.2f}/10.0",
        }
