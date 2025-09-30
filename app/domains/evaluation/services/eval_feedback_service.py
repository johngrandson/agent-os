"""Evaluation feedback service for processing evaluation results"""

from typing import Any

import httpx
from app.domains.evaluation.events.publisher import EvaluationEventPublisher
from core.config import Config
from core.logger import get_module_logger


logger = get_module_logger(__name__)


class EvalFeedbackService:
    """Service for processing evaluation feedback and converting to knowledge"""

    def __init__(self, event_publisher: EvaluationEventPublisher, config: Config):
        self.event_publisher = event_publisher
        self.config = config

    async def process_eval_failure(self, eval_id: str, agent_id: str) -> dict[str, Any]:
        """Process failed evaluation and publish event for knowledge conversion

        Args:
            eval_id: Evaluation run ID from AgentOS
            agent_id: Agent ID associated with the evaluation

        Returns:
            Dictionary with evaluation data and processing status

        Raises:
            ValueError: If evaluation score >= 8.0 or validation fails
            Exception: If API call or event publishing fails
        """
        # Fetch evaluation from AgentOS
        eval_response = await self._fetch_evaluation(eval_id)
        eval_data = eval_response.get("eval_data", {})
        eval_input = eval_response.get("eval_input", {})

        # Validate evaluation failed (score < 8.0)
        score = eval_data.get("avg_score", 0)
        if score >= 8.0:
            msg = (
                f"Evaluation {eval_id} passed (score: {score}). "
                "Only failed evaluations can be processed."
            )
            logger.warning(f"⚠️  {msg}")
            raise ValueError(msg)

        # Extract failure reason from results
        failure_reason = self._extract_failure_reason(eval_response)
        if not failure_reason:
            msg = f"No failure reason found in evaluation {eval_id}"
            logger.warning(f"⚠️  {msg}")
            raise ValueError(msg)

        # Prepare event data
        event_data = {
            "eval_id": eval_id,
            "agent_id": agent_id,
            "score": score,
            "input": eval_input.get("input", ""),
            "expected_response": eval_input.get("expected_output", ""),
            "failure_reason": failure_reason,
        }

        # Publish evaluation.failed event
        logger.info(
            f"📊 Publishing evaluation.failed event for agent {agent_id[:8]} (score: {score})"
        )
        await self.event_publisher.eval_failed(agent_id, event_data)

        return {
            "eval_id": eval_id,
            "agent_id": agent_id,
            "score": score,
            "feedback_added": True,
            "message": f"Evaluation feedback queued for processing (score: {score})",
        }

    async def _fetch_evaluation(self, eval_id: str) -> dict[str, Any]:
        """Fetch evaluation data from AgentOS API

        Args:
            eval_id: Evaluation run ID

        Returns:
            Evaluation data dictionary

        Raises:
            Exception: If API call fails
        """
        base_url = self.config.AGNO_API_BASE_URL
        url = f"{base_url}/eval-runs/{eval_id}"

        logger.info(f"🔍 Fetching evaluation {eval_id} from {url}")

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url)
                response.raise_for_status()
                eval_data = response.json()

                logger.info(f"✅ Successfully fetched evaluation {eval_id}")
                return eval_data

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                msg = f"Evaluation {eval_id} not found"
                logger.error(f"❌ {msg}")
                raise ValueError(msg) from e
            msg = f"Failed to fetch evaluation {eval_id}: {e}"
            logger.error(f"❌ {msg}")
            raise Exception(msg) from e
        except Exception as e:
            msg = f"Error fetching evaluation {eval_id}: {e}"
            logger.error(f"❌ {msg}")
            raise Exception(msg) from e

    def _extract_failure_reason(self, eval_response: dict[str, Any]) -> str:
        """Extract failure reason from evaluation results

        Args:
            eval_response: Full evaluation response from AgentOS

        Returns:
            Failure reason text or empty string if not found
        """
        # Results are nested inside eval_data field
        eval_data = eval_response.get("eval_data", {})
        results = eval_data.get("results", [])
        if not results:
            return ""

        # Get reason from first result
        first_result = results[0]
        reason = first_result.get("reason", "")

        return reason
