import uuid
from typing import List, Optional, Tuple
from sqlalchemy import select, func, and_, update
from sqlalchemy.orm import selectinload

from app.knowledge.knowledge import (
    KnowledgeContent,
    KnowledgeVector,
    AgentMemory,
    KnowledgeContext,
    SemanticSearch,
    MemoryType,
    MemoryPriority,
    KnowledgeSource,
)
from infrastructure.database.session import session


class KnowledgeRepository:
    async def save_content(self, content: KnowledgeContent) -> KnowledgeContent:
        session.add(content)
        await session.flush()
        return content

    async def save_vector(self, vector: KnowledgeVector) -> KnowledgeVector:
        session.add(vector)
        await session.flush()
        return vector

    async def get_content_by_id(
        self, content_id: uuid.UUID
    ) -> Optional[KnowledgeContent]:
        stmt = select(KnowledgeContent).where(KnowledgeContent.id == content_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_contents_by_agent(
        self, agent_id: uuid.UUID, limit: int = 10
    ) -> List[KnowledgeContent]:
        stmt = (
            select(KnowledgeContent)
            .where(KnowledgeContent.agent_id == agent_id)
            .options(selectinload(KnowledgeContent.vectors))
            .limit(limit)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def search_vectors_by_similarity(
        self,
        agent_id: uuid.UUID,
        embedding: List[float],
        limit: int = 5,
        threshold: float = 0.7,
    ) -> List[KnowledgeVector]:
        """Search for similar vectors using pgvector cosine similarity"""
        stmt = (
            select(KnowledgeVector)
            .join(KnowledgeContent)
            .where(
                KnowledgeContent.agent_id == agent_id,
                KnowledgeVector.embedding.cosine_distance(embedding) < (1 - threshold),
            )
            .order_by(KnowledgeVector.embedding.cosine_distance(embedding))
            .limit(limit)
        )

        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def delete_content(self, content_id: uuid.UUID) -> bool:
        content = await self.get_content_by_id(content_id)
        if content:
            await session.delete(content)
            return True
        return False

    async def update_access_count(self, content_id: uuid.UUID) -> None:
        stmt = select(KnowledgeContent).where(KnowledgeContent.id == content_id)
        result = await session.execute(stmt)
        content = result.scalar_one_or_none()
        if content:
            content.access_count += 1
            await session.flush()

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

    async def archive_memory(self, memory_id: uuid.UUID) -> bool:
        """Archive a memory"""
        stmt = (
            update(AgentMemory)
            .where(AgentMemory.id == memory_id)
            .values(is_archived=True)
        )
        result = await session.execute(stmt)
        return result.rowcount > 0

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

    async def get_search_history(
        self,
        agent_id: Optional[uuid.UUID] = None,
        search_type: Optional[str] = None,
        session_id: Optional[uuid.UUID] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[SemanticSearch]:
        """Get semantic search history"""
        stmt = select(SemanticSearch)

        if agent_id:
            stmt = stmt.where(SemanticSearch.agent_id == agent_id)
        if search_type:
            stmt = stmt.where(SemanticSearch.search_type == search_type)
        if session_id:
            stmt = stmt.where(SemanticSearch.task_id == session_id)

        stmt = stmt.offset(skip).limit(limit).order_by(SemanticSearch.created_at.desc())

        result = await session.execute(stmt)
        return list(result.scalars().all())
