import uuid
import time
from typing import List, Optional, Dict, Any, Tuple
from openai import AsyncOpenAI

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
from app.knowledge.repositories.knowledge_repository import KnowledgeRepository
from app.events.bus import EventBus
from app.knowledge.events import KnowledgeEvent
from infrastructure.database import Transactional


class KnowledgeService:
    def __init__(
        self,
        *,
        repository: KnowledgeRepository,
        openai_client: AsyncOpenAI,
        event_bus: EventBus,
    ):
        self.repository = repository
        self.openai_client = openai_client
        self.event_bus = event_bus

    @Transactional()
    async def add_content(
        self,
        agent_id: uuid.UUID,
        name: str,
        content: str,
        description: Optional[str] = None,
    ) -> KnowledgeContent:
        """Add content and generate embeddings following Agno's pattern"""

        # Create knowledge content record
        knowledge_content = KnowledgeContent(
            agent_id=agent_id, name=name, description=description, content_type="text"
        )
        await self.repository.save_content(knowledge_content)

        # Chunk content (simple sentence-based chunking)
        chunks = self._chunk_content(content)

        # Generate embeddings and store vectors
        for chunk in chunks:
            embedding = await self._generate_embedding(chunk)
            vector = KnowledgeVector(
                content_id=knowledge_content.id, chunk_text=chunk, embedding=embedding
            )
            await self.repository.save_vector(vector)

        # Emit knowledge creation event
        await self.event_bus.emit(
            KnowledgeEvent.memory_created(
                memory_id=str(knowledge_content.id),
                agent_id=str(agent_id),
                data={
                    "name": name,
                    "content_type": "text",
                    "chunks_count": len(chunks),
                    "has_embedding": True,
                },
            )
        )

        return knowledge_content

    async def search_knowledge(
        self, agent_id: uuid.UUID, query: str, limit: int = 5, threshold: float = 0.7
    ) -> List[str]:
        """Search knowledge using vector similarity - Agno's core search pattern"""
        query_embedding = await self._generate_embedding(query)

        vectors = await self.repository.search_vectors_by_similarity(
            agent_id=agent_id,
            embedding=query_embedding,
            limit=limit,
            threshold=threshold,
        )

        # Update access counts for found content
        content_ids = {vector.content_id for vector in vectors}
        for content_id in content_ids:
            await self.repository.update_access_count(content_id)

        # Emit knowledge search event
        await self.event_bus.emit(
            KnowledgeEvent.knowledge_searched(
                agent_id=str(agent_id), query=query, results_count=len(vectors)
            )
        )

        return [vector.chunk_text for vector in vectors]

    async def get_agent_knowledge_contents(
        self, agent_id: uuid.UUID, limit: int = 10
    ) -> List[KnowledgeContent]:
        """Get all knowledge contents for an agent"""
        return await self.repository.get_contents_by_agent(
            agent_id=agent_id, limit=limit
        )

    @Transactional()
    async def delete_content(self, content_id: uuid.UUID) -> bool:
        """Delete knowledge content and all associated vectors"""
        success = await self.repository.delete_content(content_id)

        if success:
            # Emit knowledge deletion event
            await self.event_bus.emit(
                KnowledgeEvent(
                    event_type="memory.deleted",
                    memory_id=str(content_id),
                    data={"deleted": True, "content_type": "text"},
                    source="knowledge_service",
                )
            )

        return success

    def _chunk_content(self, content: str, max_chunk_size: int = 500) -> List[str]:
        """Simple sentence-based chunking following Agno's approach"""
        sentences = content.split(". ")
        chunks = []
        current_chunk = ""

        for sentence in sentences:
            if len(current_chunk + sentence) < max_chunk_size:
                current_chunk += sentence + ". "
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence + ". "

        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks

    async def _generate_embedding(self, text: str) -> List[float]:
        """Generate OpenAI embedding following Agno's pattern"""
        response = await self.openai_client.embeddings.create(
            model="text-embedding-ada-002", input=text
        )
        return response.data[0].embedding

    # Enhanced Knowledge Methods

    @Transactional()
    async def create_agent_memory(
        self,
        agent_id: uuid.UUID,
        content: str,
        memory_type: MemoryType,
        source: KnowledgeSource,
        summary: Optional[str] = None,
        keywords: Optional[List[str]] = None,
        priority: MemoryPriority = MemoryPriority.MEDIUM,
        context_data: Optional[Dict[str, Any]] = None,
        related_task_id: Optional[uuid.UUID] = None,
        retention_days: Optional[int] = None,
        generate_embedding: bool = True,
    ) -> AgentMemory:
        """Create a new agent memory with optional embedding generation"""

        # Generate embedding if requested
        embedding = None
        if generate_embedding:
            embedding = await self._generate_embedding(content)

        # Calculate expiry if retention_days is set
        expires_at = None
        if retention_days:
            from datetime import datetime, timedelta

            expires_at = (
                datetime.utcnow() + timedelta(days=retention_days)
            ).isoformat()

        memory = AgentMemory(
            agent_id=agent_id,
            content=content,
            summary=summary,
            keywords=keywords or [],
            embedding=embedding,
            memory_type=memory_type,
            priority=priority,
            source=source,
            context_data=context_data or {},
            related_task_id=related_task_id,
            retention_days=retention_days,
            expires_at=expires_at,
        )

        saved_memory = await self.repository.save_agent_memory(memory)

        # Emit memory creation event
        await self.event_bus.emit(
            KnowledgeEvent.memory_created(
                memory_id=str(saved_memory.id),
                agent_id=str(agent_id),
                data={
                    "memory_type": memory_type.value,
                    "source": source.value,
                    "has_embedding": embedding is not None,
                },
            )
        )

        return saved_memory

    async def get_agent_memories(
        self,
        agent_id: uuid.UUID,
        memory_type: Optional[MemoryType] = None,
        priority: Optional[MemoryPriority] = None,
        source: Optional[KnowledgeSource] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[AgentMemory]:
        """Get agent memories with optional filtering"""
        return await self.repository.get_agent_memories(
            agent_id=agent_id,
            memory_type=memory_type,
            priority=priority,
            source=source,
            skip=skip,
            limit=limit,
        )

    async def search_memories_semantic(
        self,
        agent_id: uuid.UUID,
        query: str,
        similarity_threshold: float = 0.8,
        limit: int = 10,
        memory_type: Optional[MemoryType] = None,
    ) -> List[Tuple[AgentMemory, float]]:
        """Search agent memories using semantic similarity"""
        query_embedding = await self._generate_embedding(query)

        results = await self.repository.search_memories_by_similarity(
            agent_id=agent_id,
            embedding=query_embedding,
            similarity_threshold=similarity_threshold,
            limit=limit,
            memory_type=memory_type,
        )

        # Update access counts
        for memory, _ in results:
            await self.repository.update_memory_access(memory.id)

        # Emit search event
        await self.event_bus.emit(
            KnowledgeEvent.knowledge_searched(
                agent_id=str(agent_id), query=query, results_count=len(results)
            )
        )

        return results

    @Transactional()
    async def archive_memory(self, memory_id: uuid.UUID) -> bool:
        """Archive an agent memory"""
        return await self.repository.archive_memory(memory_id)

    @Transactional()
    async def create_knowledge_context(
        self,
        agent_id: uuid.UUID,
        context_type: str,
        context_key: str,
        context_value: Dict[str, Any],
        priority: int = 5,
        expiry: Optional[str] = None,
        generate_embedding: bool = True,
    ) -> KnowledgeContext:
        """Create a knowledge context for an agent"""

        # Generate embedding from context key and value
        embedding = None
        if generate_embedding:
            context_text = f"{context_key}: {str(context_value)}"
            embedding = await self._generate_embedding(context_text)

        context = KnowledgeContext(
            agent_id=agent_id,
            context_type=context_type,
            context_key=context_key,
            context_value=context_value,
            embedding=embedding,
            priority=priority,
            expiry=expiry,
        )

        return await self.repository.save_knowledge_context(context)

    async def get_knowledge_contexts(
        self,
        agent_id: uuid.UUID,
        context_type: Optional[str] = None,
        is_active: bool = True,
        skip: int = 0,
        limit: int = 100,
    ) -> List[KnowledgeContext]:
        """Get knowledge contexts for an agent"""
        return await self.repository.get_knowledge_contexts(
            agent_id=agent_id,
            context_type=context_type,
            is_active=is_active,
            skip=skip,
            limit=limit,
        )

    async def get_search_history(
        self,
        agent_id: Optional[uuid.UUID] = None,
        search_type: Optional[str] = None,
        session_id: Optional[uuid.UUID] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[SemanticSearch]:
        """Get semantic search history"""
        return await self.repository.get_search_history(
            agent_id=agent_id,
            search_type=search_type,
            session_id=session_id,
            skip=skip,
            limit=limit,
        )
