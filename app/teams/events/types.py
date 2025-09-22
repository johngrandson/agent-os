"""
Team event types
"""

from enum import Enum


class TeamEventType(str, Enum):
    """Types of team-related events"""

    TEAM_CREATED = "team.created"
    TEAM_UPDATED = "team.updated"
    TEAM_DELETED = "team.deleted"
    MEMBER_ADDED = "team.member_added"
    MEMBER_REMOVED = "team.member_removed"
    COORDINATION_STARTED = "team.coordination_started"
