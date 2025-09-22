"""
Team domain event classes
"""

from typing import Dict, Any, Optional
from app.events.core import BaseEvent, EventPriority
from .types import TeamEventType


class TeamEvent(BaseEvent):
    """Team-related events"""

    team_id: Optional[str] = None
    agent_id: Optional[str] = None

    @classmethod
    def team_created(
        cls, team_id: str, data: Dict[str, Any] = None, **kwargs
    ) -> "TeamEvent":
        return cls(
            event_type=TeamEventType.TEAM_CREATED,
            team_id=team_id,
            data=data or {},
            source="team_service",
            **kwargs,
        )

    @classmethod
    def team_updated(
        cls, team_id: str, data: Dict[str, Any] = None, **kwargs
    ) -> "TeamEvent":
        return cls(
            event_type=TeamEventType.TEAM_UPDATED,
            team_id=team_id,
            data=data or {},
            source="team_service",
            **kwargs,
        )

    @classmethod
    def team_deleted(
        cls, team_id: str, data: Dict[str, Any] = None, **kwargs
    ) -> "TeamEvent":
        return cls(
            event_type=TeamEventType.TEAM_DELETED,
            team_id=team_id,
            data=data or {},
            source="team_service",
            **kwargs,
        )

    @classmethod
    def member_added(
        cls, team_id: str, agent_id: str, data: Dict[str, Any] = None, **kwargs
    ) -> "TeamEvent":
        return cls(
            event_type=TeamEventType.MEMBER_ADDED,
            team_id=team_id,
            agent_id=agent_id,
            data=data or {},
            source="team_service",
            **kwargs,
        )

    @classmethod
    def member_removed(
        cls, team_id: str, agent_id: str, data: Dict[str, Any] = None, **kwargs
    ) -> "TeamEvent":
        return cls(
            event_type=TeamEventType.MEMBER_REMOVED,
            team_id=team_id,
            agent_id=agent_id,
            data=data or {},
            source="team_service",
            **kwargs,
        )

    @classmethod
    def coordination_started(
        cls, team_id: str, data: Dict[str, Any] = None, **kwargs
    ) -> "TeamEvent":
        return cls(
            event_type=TeamEventType.COORDINATION_STARTED,
            team_id=team_id,
            data=data or {},
            source="team_service",
            **kwargs,
        )
