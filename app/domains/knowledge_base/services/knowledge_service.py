"""Knowledge service for managing agent knowledge operations"""

from typing import Any

from app.domains.knowledge_base.services.agent_knowledge_factory import AgentKnowledgeFactory
from core.logger import get_module_logger


logger = get_module_logger(__name__)


class KnowledgeService:
    """Service for managing agent knowledge operations"""

    def __init__(self, knowledge_factory: AgentKnowledgeFactory):
        self.knowledge_factory = knowledge_factory

    async def add_eval_feedback(
        self,
        agent_id: str,
        agent_name: str,
        eval_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Add evaluation feedback to agent knowledge

        Args:
            agent_id: Agent ID
            agent_name: Agent name
            eval_data: Evaluation data including failure reason

        Returns:
            Dictionary with operation status

        Raises:
            Exception: If knowledge addition fails
        """
        eval_id = eval_data.get("eval_id", "unknown")
        score = eval_data.get("score", 0)

        logger.info(f"📚 Adding eval feedback to knowledge for agent {agent_name} [{agent_id[:8]}]")

        try:
            # Get or create knowledge base for agent
            knowledge = await self.knowledge_factory.create_knowledge_for_agent(
                agent_id=agent_id,
                agent_name=agent_name,
            )

            # Format feedback content
            content = self._format_eval_feedback(eval_data)

            # Prepare metadata
            metadata = {
                "agent_id": agent_id,
                "source": "eval_failure",
                "eval_id": eval_id,
                "score": score,
            }

            # Add content to knowledge base
            # Run in thread pool to avoid asyncio.run() conflicts with FastStream
            import asyncio
            from functools import partial

            loop = asyncio.get_event_loop()
            add_content_fn = partial(
                knowledge.add_content,
                name=f"Evaluation Feedback - {eval_id}",
                text_content=content,
                metadata=metadata,
                skip_if_exists=True,
            )

            # Suppress only ResourceWarnings from httpx transport cleanup
            # These are benign warnings that don't affect functionality
            import warnings

            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", category=ResourceWarning, module="httpx")
                await loop.run_in_executor(None, add_content_fn)

            logger.info(
                f"✅ Successfully added eval feedback {eval_id} to knowledge for agent {agent_name}"
            )

            return {
                "agent_id": agent_id,
                "eval_id": eval_id,
                "status": "success",
                "message": f"Added evaluation feedback to knowledge for {agent_name}",
            }

        except Exception as e:
            logger.error(f"❌ Failed to add eval feedback {eval_id} to knowledge: {e}")
            raise Exception(f"Failed to add evaluation feedback to knowledge: {e}") from e

    def _format_eval_feedback(self, eval_data: dict[str, Any]) -> str:
        """Format evaluation feedback as structured markdown

        Args:
            eval_data: Evaluation data

        Returns:
            Formatted markdown content
        """
        eval_id = eval_data.get("eval_id", "unknown")
        score = eval_data.get("score", 0)
        input_text = eval_data.get("input", "N/A")
        expected_response = eval_data.get("expected_response", "N/A")
        failure_reason = eval_data.get("failure_reason", "No reason provided")

        content = f"""# Evaluation Feedback

## Evaluation Details
- **Evaluation ID**: {eval_id}
- **Score**: {score}/10.0
- **Status**: Failed

## Input
{input_text}

## Expected Response
{expected_response}

## What Went Wrong
{failure_reason}

## Improvement Guidance
Review this feedback carefully to understand the gap between expected and actual behavior.
Focus on addressing the specific issues mentioned in the failure reason to improve future responses.
"""

        return content
