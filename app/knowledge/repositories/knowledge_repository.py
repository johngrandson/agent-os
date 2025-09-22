import uuid
from typing import List, Optional, Tuple
from sqlalchemy import select, func, and_, update
from sqlalchemy.orm import selectinload

from app.knowledge.knowledge import (
    AgentMemory,
    KnowledgeContext,
    KnowledgeContent,
    KnowledgeChunk,
    MemoryType,
    MemoryPriority,
    KnowledgeSource,
    ContentType,
    ContentStatus,
)
from infrastructure.database.session import session


class KnowledgeRepository:
    # Enhanced Knowledge Methods

    async def save_agent_memory(self, memory: AgentMemory) -> AgentMemory:
        """Save agent memory to database"""
        session.add(memory)
        await session.flush()
        return memory

    async def get_agent_memories(
        self,
        agent_id: uuid.UUID,
        memory_type: Optional[MemoryType] = None,
        priority: Optional[MemoryPriority] = None,
        source: Optional[KnowledgeSource] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[AgentMemory]:
        """Get agent memories with filtering"""
        stmt = select(AgentMemory).where(
            AgentMemory.agent_id == agent_id, AgentMemory.is_archived == False
        )

        if memory_type:
            stmt = stmt.where(AgentMemory.memory_type == memory_type)
        if priority:
            stmt = stmt.where(AgentMemory.priority == priority)
        if source:
            stmt = stmt.where(AgentMemory.source == source)

        stmt = stmt.offset(skip).limit(limit).order_by(AgentMemory.created_at.desc())

        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def search_memories_by_similarity(
        self,
        agent_id: uuid.UUID,
        embedding: List[float],
        similarity_threshold: float = 0.8,
        limit: int = 10,
        memory_type: Optional[MemoryType] = None,
    ) -> List[Tuple[AgentMemory, float]]:
        """Search memories using vector similarity"""
        stmt = select(
            AgentMemory,
            AgentMemory.embedding.cosine_similarity(embedding).label("similarity"),
        ).where(
            AgentMemory.agent_id == agent_id,
            AgentMemory.is_archived == False,
            AgentMemory.embedding.cosine_similarity(embedding) >= similarity_threshold,
        )

        if memory_type:
            stmt = stmt.where(AgentMemory.memory_type == memory_type)

        stmt = stmt.order_by(
            AgentMemory.embedding.cosine_similarity(embedding).desc()
        ).limit(limit)

        result = await session.execute(stmt)
        return [(memory, float(similarity)) for memory, similarity in result.all()]

    async def update_memory_access(self, memory_id: uuid.UUID) -> None:
        """Update memory access count and timestamp"""
        from datetime import datetime

        stmt = (
            update(AgentMemory)
            .where(AgentMemory.id == memory_id)
            .values(
                access_count=AgentMemory.access_count + 1,
                last_accessed=datetime.utcnow().isoformat(),
            )
        )
        await session.execute(stmt)

    async def save_knowledge_context(
        self, context: KnowledgeContext
    ) -> KnowledgeContext:
        """Save knowledge context to database"""
        session.add(context)
        await session.flush()
        return context

    async def get_knowledge_contexts(
        self,
        agent_id: uuid.UUID,
        context_type: Optional[str] = None,
        is_active: bool = True,
        skip: int = 0,
        limit: int = 100,
    ) -> List[KnowledgeContext]:
        """Get knowledge contexts for an agent"""
        stmt = select(KnowledgeContext).where(
            KnowledgeContext.agent_id == agent_id,
            KnowledgeContext.is_active == is_active,
        )

        if context_type:
            stmt = stmt.where(KnowledgeContext.context_type == context_type)

        stmt = (
            stmt.offset(skip).limit(limit).order_by(KnowledgeContext.created_at.desc())
        )

        result = await session.execute(stmt)
        return list(result.scalars().all())

    # Knowledge Content Methods

    async def create_knowledge_content(
        self, content: KnowledgeContent
    ) -> KnowledgeContent:
        """Create knowledge content"""
        session.add(content)
        await session.flush()
        return content

    async def get_knowledge_content_by_id(
        self, content_id: uuid.UUID
    ) -> Optional[KnowledgeContent]:
        """Get knowledge content by ID"""
        stmt = select(KnowledgeContent).where(KnowledgeContent.id == content_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_knowledge_contents(
        self,
        agent_id: uuid.UUID,
        content_type: Optional[ContentType] = None,
        status: Optional[ContentStatus] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[KnowledgeContent]:
        """Get knowledge contents for an agent"""
        stmt = select(KnowledgeContent).where(KnowledgeContent.agent_id == agent_id)

        if content_type:
            stmt = stmt.where(KnowledgeContent.content_type == content_type)
        if status:
            stmt = stmt.where(KnowledgeContent.status == status)

        stmt = (
            stmt.offset(skip).limit(limit).order_by(KnowledgeContent.created_at.desc())
        )

        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def update_content_status(
        self, content_id: uuid.UUID, status: ContentStatus, total_chunks: int = 0
    ) -> None:
        """Update content status and chunk count"""
        stmt = (
            update(KnowledgeContent)
            .where(KnowledgeContent.id == content_id)
            .values(status=status, total_chunks=total_chunks)
        )
        await session.execute(stmt)

    async def delete_knowledge_content(self, content_id: uuid.UUID) -> bool:
        """Delete knowledge content and its chunks"""
        content = await self.get_knowledge_content_by_id(content_id)
        if not content:
            return False

        # Delete chunks first (handled by cascade)
        await session.delete(content)
        return True

    # Knowledge Chunk Methods

    async def create_knowledge_chunk(self, chunk: KnowledgeChunk) -> KnowledgeChunk:
        """Create knowledge chunk"""
        session.add(chunk)
        await session.flush()
        return chunk

    async def get_content_chunks(
        self, content_id: uuid.UUID, skip: int = 0, limit: int = 100
    ) -> List[KnowledgeChunk]:
        """Get chunks for a content"""
        stmt = (
            select(KnowledgeChunk)
            .where(KnowledgeChunk.content_id == content_id)
            .order_by(KnowledgeChunk.chunk_index)
            .offset(skip)
            .limit(limit)
        )

        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def search_chunks_by_similarity(
        self,
        agent_id: uuid.UUID,
        embedding: List[float],
        similarity_threshold: float = 0.8,
        limit: int = 10,
        content_type: Optional[ContentType] = None,
    ) -> List[Tuple[KnowledgeChunk, KnowledgeContent, float]]:
        """Search chunks using vector similarity with content metadata"""
        stmt = (
            select(
                KnowledgeChunk,
                KnowledgeContent,
                KnowledgeChunk.embedding.cosine_similarity(embedding).label(
                    "similarity"
                ),
            )
            .join(KnowledgeContent, KnowledgeChunk.content_id == KnowledgeContent.id)
            .where(
                KnowledgeChunk.agent_id == agent_id,
                KnowledgeContent.status == ContentStatus.READY,
                KnowledgeChunk.embedding.cosine_similarity(embedding)
                >= similarity_threshold,
            )
        )

        if content_type:
            stmt = stmt.where(KnowledgeContent.content_type == content_type)

        stmt = stmt.order_by(
            KnowledgeChunk.embedding.cosine_similarity(embedding).desc()
        ).limit(limit)

        result = await session.execute(stmt)
        return [
            (chunk, content, float(similarity))
            for chunk, content, similarity in result.all()
        ]

    async def count_content_chunks(self, content_id: uuid.UUID) -> int:
        """Count chunks for a content"""
        stmt = select(func.count(KnowledgeChunk.id)).where(
            KnowledgeChunk.content_id == content_id
        )
        result = await session.execute(stmt)
        return result.scalar() or 0
