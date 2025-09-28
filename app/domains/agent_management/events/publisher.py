"""Agent event publisher"""

from typing import Any

from app.shared.events.base import BaseEventPublisher

from .events import AgentEvent


class AgentEventPublisher(BaseEventPublisher):
    """Publisher for agent domain events"""

    def get_domain_prefix(self) -> str:
        return "agents"

    async def agent_created(self, agent_id: str, agent_data: dict[str, Any]) -> None:
        """Publish agent created event"""
        event = AgentEvent.created(agent_id, agent_data)
        await self.publish_domain_event("created", event)

    async def agent_updated(self, agent_id: str, agent_data: dict[str, Any]) -> None:
        """Publish agent updated event"""
        event = AgentEvent.updated(agent_id, agent_data)
        await self.publish_domain_event("updated", event)

    async def agent_deleted(self, agent_id: str) -> None:
        """Publish agent deleted event"""
        event = AgentEvent.deleted(agent_id)
        await self.publish_domain_event("deleted", event)

    async def agent_knowledge_created(self, agent_id: str, knowledge_data: dict[str, Any]) -> None:
        """Publish agent knowledge created event"""
        event = AgentEvent.knowledge_created(agent_id, knowledge_data)
        await self.publish_domain_event("knowledge_created", event)
