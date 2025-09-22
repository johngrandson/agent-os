from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any, TYPE_CHECKING
from enum import Enum

from sqlalchemy import String, Text, Integer, DateTime, ForeignKey, JSON, Boolean, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector

from infrastructure.database import Base
from infrastructure.database.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.agents.agent import Agent


class MemoryType(str, Enum):
    """Types of memories"""

    TASK_RESULT = "task_result"
    LEARNING = "learning"
    EXPERIENCE = "experience"
    CONTEXT = "context"
    FACT = "fact"


class MemoryPriority(str, Enum):
    """Memory priority levels"""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class KnowledgeSource(str, Enum):
    """Sources of knowledge"""

    USER_INPUT = "user_input"
    AGENT_REASONING = "agent_reasoning"
    TOOL_OUTPUT = "tool_output"
    EXTERNAL_API = "external_api"
    DOCUMENT = "document"
    WEB_SEARCH = "web_search"


class KnowledgeContent(Base, TimestampMixin):
    """Knowledge content metadata storage"""

    __tablename__ = "knowledge_contents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    content_type: Mapped[str] = mapped_column(String(50), default="text")
    content_metadata: Mapped[Optional[dict]] = mapped_column(
        JSON, nullable=True, default={}
    )
    access_count: Mapped[int] = mapped_column(Integer, default=0)

    # Relationships
    agent: Mapped["Agent"] = relationship("Agent", back_populates="knowledge_contents")
    vectors: Mapped[List["KnowledgeVector"]] = relationship(
        "KnowledgeVector", back_populates="content", cascade="all, delete-orphan"
    )


class KnowledgeVector(Base):
    """Vector embeddings storage with pgvector"""

    __tablename__ = "knowledge_vectors"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    content_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_contents.id", ondelete="CASCADE"),
        nullable=False,
    )
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[Optional[List[float]]] = mapped_column(
        Vector(1536), nullable=True
    )  # OpenAI embedding dimension
    content_metadata: Mapped[Optional[dict]] = mapped_column(
        JSON, nullable=True, default={}
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    content: Mapped["KnowledgeContent"] = relationship(
        "KnowledgeContent", back_populates="vectors"
    )


class AgentMemory(Base, TimestampMixin):
    """Enhanced agent memory with vector embeddings"""

    __tablename__ = "agent_memories"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id"), nullable=False
    )

    # Memory content
    content: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=True)
    keywords: Mapped[List[str]] = mapped_column(JSON, nullable=True)

    # Vector embedding for semantic search
    embedding: Mapped[List[float]] = mapped_column(Vector(1536), nullable=True)

    # Memory metadata
    memory_type: Mapped[MemoryType] = mapped_column(String(50), nullable=False)
    priority: Mapped[MemoryPriority] = mapped_column(
        String(50), default=MemoryPriority.MEDIUM.value
    )
    source: Mapped[KnowledgeSource] = mapped_column(String(50), nullable=False)

    # Context and relationships
    context_data: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=True)
    related_task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=True
    )

    # Access and usage
    access_count: Mapped[int] = mapped_column(Integer, default=0)
    last_accessed: Mapped[str] = mapped_column(nullable=True)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False)

    # Retention policy
    retention_days: Mapped[int] = mapped_column(Integer, nullable=True)
    expires_at: Mapped[str] = mapped_column(nullable=True)

    # Relationships
    agent: Mapped["Agent"] = relationship("Agent", lazy="selectin")
    related_task: Mapped["Task"] = relationship("Task", lazy="selectin")

    __table_args__ = (
        Index("ix_agent_memories_agent_id", "agent_id"),
        Index("ix_agent_memories_memory_type", "memory_type"),
        Index("ix_agent_memories_priority", "priority"),
        Index("ix_agent_memories_source", "source"),
        Index("ix_agent_memories_embedding", "embedding", postgresql_using="ivfflat"),
    )


class KnowledgeContext(Base, TimestampMixin):
    """Contextual knowledge for agents"""

    __tablename__ = "knowledge_contexts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id"), nullable=False
    )

    # Context details
    context_type: Mapped[str] = mapped_column(String(100), nullable=False)
    context_key: Mapped[str] = mapped_column(String(255), nullable=False)
    context_value: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)

    # Vector embedding for semantic matching
    embedding: Mapped[List[float]] = mapped_column(Vector(1536), nullable=True)

    # Metadata
    priority: Mapped[int] = mapped_column(Integer, default=5)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    expiry: Mapped[str] = mapped_column(nullable=True)

    # Usage tracking
    usage_count: Mapped[int] = mapped_column(Integer, default=0)
    last_used: Mapped[str] = mapped_column(nullable=True)

    # Relationships
    agent: Mapped["Agent"] = relationship("Agent", lazy="selectin")

    __table_args__ = (
        Index("ix_knowledge_contexts_agent_id", "agent_id"),
        Index("ix_knowledge_contexts_context_type", "context_type"),
        Index("ix_knowledge_contexts_context_key", "context_key"),
        Index(
            "ix_knowledge_contexts_embedding", "embedding", postgresql_using="ivfflat"
        ),
        Index("ix_knowledge_contexts_priority", "priority"),
    )


class SemanticSearch(Base, TimestampMixin):
    """Semantic search history and results"""

    __tablename__ = "semantic_searches"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id"), nullable=True
    )

    # Search details
    query: Mapped[str] = mapped_column(Text, nullable=False)
    query_embedding: Mapped[List[float]] = mapped_column(Vector(1536), nullable=True)

    # Search parameters
    search_type: Mapped[str] = mapped_column(String(50), nullable=False)
    filters: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=True)
    limit_results: Mapped[int] = mapped_column(Integer, default=10)

    # Results
    results_count: Mapped[int] = mapped_column(Integer, default=0)
    results: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    # Performance metrics
    execution_time: Mapped[float] = mapped_column(nullable=True)
    similarity_threshold: Mapped[float] = mapped_column(default=0.8)

    # Context
    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=True
    )

    # Relationships
    agent: Mapped["Agent"] = relationship("Agent", lazy="selectin")
    task: Mapped["Task"] = relationship("Task", lazy="selectin")

    __table_args__ = (
        Index("ix_semantic_searches_agent_id", "agent_id"),
        Index("ix_semantic_searches_search_type", "search_type"),
        Index(
            "ix_semantic_searches_query_embedding",
            "query_embedding",
            postgresql_using="ivfflat",
        ),
    )
