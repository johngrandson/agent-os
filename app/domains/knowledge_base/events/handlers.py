"""Knowledge base event handlers"""

from typing import Any

from app.domains.evaluation.events.events import EvalEventPayload
from app.domains.knowledge_base.services.knowledge_service import KnowledgeService
from core.logger import get_module_logger


logger = get_module_logger(__name__)


async def handle_eval_failure(
    data: EvalEventPayload,
    knowledge_service: KnowledgeService,
    agent_repository: Any,
) -> None:
    """Handle evaluation failure events by adding feedback to agent knowledge

    Args:
        data: Event payload with evaluation failure data
        knowledge_service: Service for managing knowledge operations
        agent_repository: Repository for fetching agent details
    """
    agent_id = data["entity_id"]
    eval_data = data["data"]
    eval_id = eval_data.get("eval_id", "unknown")
    score = eval_data.get("score", 0)

    logger.info(
        f"📊 HANDLER: Processing eval failure {eval_id} for agent {agent_id[:8]} (score: {score})"
    )

    try:
        # Import UUID for agent lookup
        import uuid

        # Fetch agent details
        agent_uuid = uuid.UUID(agent_id)
        agent = await agent_repository.get_agent_by_id(agent_id=agent_uuid)
        if not agent:
            logger.error(f"❌ HANDLER: Agent {agent_id[:8]} not found")
            return

        agent_name = agent.name

        # Add evaluation feedback to knowledge
        await knowledge_service.add_eval_feedback(
            agent_id=agent_id,
            agent_name=agent_name,
            eval_data=eval_data,
        )

        logger.info(
            f"✅ HANDLER: Successfully processed eval {eval_id} "
            f"for agent {agent_name} [{agent_id[:8]}]"
        )

    except Exception as e:
        logger.error(f"❌ HANDLER: Failed to process eval {eval_id} for agent {agent_id[:8]}: {e}")
        # Don't re-raise to prevent event processing from failing
        # The failure is logged and can be retried manually if needed
