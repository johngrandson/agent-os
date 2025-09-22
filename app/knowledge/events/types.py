"""
Knowledge event types
"""

from enum import Enum


class KnowledgeEventType(str, Enum):
    """Types of knowledge-related events"""

    MEMORY_CREATED = "memory.created"
    MEMORY_UPDATED = "memory.updated"
    MEMORY_DELETED = "memory.deleted"
    MEMORY_ACCESSED = "memory.accessed"
    KNOWLEDGE_SEARCHED = "knowledge.searched"
