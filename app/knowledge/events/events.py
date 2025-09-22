"""
Knowledge domain event classes
"""

from typing import Dict, Any, Optional
from app.events.core import BaseEvent, EventPriority
from .types import KnowledgeEventType


class KnowledgeEvent(BaseEvent):
    """Knowledge and memory-related events"""

    memory_id: Optional[str] = None
    agent_id: Optional[str] = None
    session_id: Optional[str] = None

    @classmethod
    def memory_created(
        cls, memory_id: str, agent_id: str, data: Dict[str, Any] = None
    ) -> "KnowledgeEvent":
        return cls(
            event_type=KnowledgeEventType.MEMORY_CREATED,
            memory_id=memory_id,
            agent_id=agent_id,
            data=data or {},
            source="knowledge_service",
        )

    @classmethod
    def memory_updated(
        cls, memory_id: str, agent_id: str, data: Dict[str, Any] = None
    ) -> "KnowledgeEvent":
        return cls(
            event_type=KnowledgeEventType.MEMORY_UPDATED,
            memory_id=memory_id,
            agent_id=agent_id,
            data=data or {},
            source="knowledge_service",
        )

    @classmethod
    def memory_deleted(
        cls, memory_id: str, agent_id: str, data: Dict[str, Any] = None
    ) -> "KnowledgeEvent":
        return cls(
            event_type=KnowledgeEventType.MEMORY_DELETED,
            memory_id=memory_id,
            agent_id=agent_id,
            data=data or {},
            source="knowledge_service",
        )

    @classmethod
    def memory_accessed(
        cls, memory_id: str, agent_id: str, data: Dict[str, Any] = None
    ) -> "KnowledgeEvent":
        return cls(
            event_type=KnowledgeEventType.MEMORY_ACCESSED,
            memory_id=memory_id,
            agent_id=agent_id,
            data=data or {},
            source="knowledge_service",
        )

    @classmethod
    def knowledge_searched(
        cls, agent_id: str, query: str, results_count: int = 0
    ) -> "KnowledgeEvent":
        return cls(
            event_type=KnowledgeEventType.KNOWLEDGE_SEARCHED,
            agent_id=agent_id,
            data={"query": query, "results_count": results_count},
            source="knowledge_service",
        )
