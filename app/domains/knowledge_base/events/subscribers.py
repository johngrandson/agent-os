"""Knowledge base event subscribers"""

from app.container import Container
from app.domains.evaluation.events.events import EvalEventPayload
from app.shared.events.domain_registry import EventRegistry

from .handlers import handle_eval_failure


# Create container instance for dependency injection
container = Container()


# Wrap handler with dependencies
async def handle_eval_failure_with_deps(data: EvalEventPayload) -> None:
    """Wrapper for handle_eval_failure with dependency injection"""
    knowledge_service = container.knowledge_service()
    agent_repository = container.agent_repository()

    await handle_eval_failure(
        data=data,
        knowledge_service=knowledge_service,
        agent_repository=agent_repository,
    )


# Evaluation events handled by knowledge_base domain
EVALUATION_EVENTS = EventRegistry(
    "evaluation",
    EvalEventPayload,
    {
        "failed": handle_eval_failure_with_deps,
    },
)
