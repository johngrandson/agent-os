from __future__ import annotations

import uuid
from typing import Optional, List, Dict, Any, TYPE_CHECKING
from enum import Enum

from sqlalchemy import String, Text, Integer, ForeignKey, JSON, Boolean, Index
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

    # Access and usage
    access_count: Mapped[int] = mapped_column(Integer, default=0)
    last_accessed: Mapped[str] = mapped_column(nullable=True)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False)

    # Retention policy
    retention_days: Mapped[int] = mapped_column(Integer, nullable=True)
    expires_at: Mapped[str] = mapped_column(nullable=True)

    # Relationships
    agent: Mapped["Agent"] = relationship("Agent", lazy="selectin")

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


class ContentType(str, Enum):
    """Types of knowledge content"""

    TEXT = "text"
    PDF = "pdf"
    DOCX = "docx"
    JSON = "json"
    HTML = "html"
    MARKDOWN = "markdown"
    CSV = "csv"


class ContentStatus(str, Enum):
    """Status of knowledge content processing"""

    UPLOADED = "uploaded"
    PROCESSING = "processing"
    PROCESSED = "processed"
    CHUNKED = "chunked"
    EMBEDDED = "embedded"
    READY = "ready"
    ERROR = "error"


class KnowledgeContent(Base, TimestampMixin):
    """Content database - tracks metadata about knowledge content"""

    __tablename__ = "knowledge_contents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id"), nullable=False
    )

    # Content metadata
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    content_type: Mapped[ContentType] = mapped_column(String(50), nullable=False)
    status: Mapped[ContentStatus] = mapped_column(
        String(50), default=ContentStatus.UPLOADED.value
    )

    # Content data
    content_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    file_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    file_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    file_hash: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True
    )  # SHA-256

    # Processing metadata
    chunk_size: Mapped[int] = mapped_column(Integer, default=1000)
    chunk_overlap: Mapped[int] = mapped_column(Integer, default=200)
    total_chunks: Mapped[int] = mapped_column(Integer, default=0)

    # Content metadata from processing
    content_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON, nullable=True
    )

    # Access tracking
    access_count: Mapped[int] = mapped_column(Integer, default=0)
    last_accessed: Mapped[Optional[str]] = mapped_column(nullable=True)

    # Relationships
    agent: Mapped["Agent"] = relationship("Agent", lazy="selectin")
    chunks: Mapped[List["KnowledgeChunk"]] = relationship(
        "KnowledgeChunk", back_populates="content", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_knowledge_contents_agent_id", "agent_id"),
        Index("ix_knowledge_contents_content_type", "content_type"),
        Index("ix_knowledge_contents_status", "status"),
        Index("ix_knowledge_contents_file_hash", "file_hash"),
    )


class KnowledgeChunk(Base, TimestampMixin):
    """Vector database - stores chunked content with embeddings"""

    __tablename__ = "knowledge_chunks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    content_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("knowledge_contents.id"), nullable=False
    )
    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id"), nullable=False
    )

    # Chunk data
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)

    # Vector embedding for semantic search
    embedding: Mapped[Optional[List[float]]] = mapped_column(
        Vector(1536), nullable=True
    )

    # Chunk metadata
    chunk_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON, nullable=True
    )
    start_position: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    end_position: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Search optimization
    keywords: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    content: Mapped["KnowledgeContent"] = relationship(
        "KnowledgeContent", back_populates="chunks"
    )
    agent: Mapped["Agent"] = relationship("Agent", lazy="selectin")

    __table_args__ = (
        Index("ix_knowledge_chunks_content_id", "content_id"),
        Index("ix_knowledge_chunks_agent_id", "agent_id"),
        Index("ix_knowledge_chunks_chunk_index", "chunk_index"),
        Index("ix_knowledge_chunks_embedding", "embedding", postgresql_using="ivfflat"),
        Index(
            "ix_knowledge_chunks_content_chunk",
            "content_id",
            "chunk_index",
            unique=True,
        ),
    )
