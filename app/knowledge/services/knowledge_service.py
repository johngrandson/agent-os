import uuid
from typing import List, Optional, Dict, Any, Tuple
from openai import AsyncOpenAI

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

    # Knowledge Content Methods - Agno-style content database

    @Transactional()
    async def create_knowledge_content(
        self,
        agent_id: uuid.UUID,
        name: str,
        content_type: ContentType,
        content_text: Optional[str] = None,
        file_path: Optional[str] = None,
        description: Optional[str] = None,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        generate_embeddings: bool = True,
    ) -> KnowledgeContent:
        """Create knowledge content following Agno's content database pattern"""
        import hashlib
        import os

        # Calculate file hash if file_path provided
        file_hash = None
        file_size = None
        if file_path and os.path.exists(file_path):
            with open(file_path, "rb") as f:
                content_bytes = f.read()
                file_hash = hashlib.sha256(content_bytes).hexdigest()
                file_size = len(content_bytes)

                # If no content_text provided, read from file (for text files)
                if not content_text and content_type in [
                    ContentType.TEXT,
                    ContentType.MARKDOWN,
                ]:
                    content_text = content_bytes.decode("utf-8")

        content = KnowledgeContent(
            agent_id=agent_id,
            name=name,
            description=description,
            content_type=content_type,
            status=ContentStatus.UPLOADED,
            content_text=content_text,
            file_path=file_path,
            file_size=file_size,
            file_hash=file_hash,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

        saved_content = await self.repository.create_knowledge_content(content)

        # Start processing if we have content_text
        if content_text and generate_embeddings:
            await self._process_content(saved_content)

        return saved_content

    async def _process_content(self, content: KnowledgeContent) -> None:
        """Process content into chunks with embeddings"""
        try:
            # Update status to processing
            await self.repository.update_content_status(
                content.id, ContentStatus.PROCESSING
            )

            if not content.content_text:
                await self.repository.update_content_status(
                    content.id, ContentStatus.ERROR
                )
                return

            # Chunk the content
            chunks = self._chunk_content_advanced(
                content.content_text, content.chunk_size, content.chunk_overlap
            )

            # Update status to chunked
            await self.repository.update_content_status(
                content.id, ContentStatus.CHUNKED, len(chunks)
            )

            # Create chunks with embeddings
            for i, chunk_text in enumerate(chunks):
                embedding = await self._generate_embedding(chunk_text)

                chunk = KnowledgeChunk(
                    content_id=content.id,
                    agent_id=content.agent_id,
                    chunk_text=chunk_text,
                    chunk_index=i,
                    embedding=embedding,
                    start_position=None,  # Could calculate if needed
                    end_position=None,
                )

                await self.repository.create_knowledge_chunk(chunk)

            # Update final status
            await self.repository.update_content_status(
                content.id, ContentStatus.READY, len(chunks)
            )

            # Emit content processed event
            await self.event_bus.emit(
                KnowledgeEvent.content_processed(
                    content_id=str(content.id),
                    agent_id=str(content.agent_id),
                    chunks_count=len(chunks),
                )
            )

        except Exception as e:
            await self.repository.update_content_status(content.id, ContentStatus.ERROR)
            # Could emit error event here
            raise e

    def _chunk_content_advanced(
        self, content: str, chunk_size: int, chunk_overlap: int
    ) -> List[str]:
        """Advanced chunking with overlap for better context preservation"""
        if len(content) <= chunk_size:
            return [content]

        chunks = []
        start = 0

        while start < len(content):
            end = start + chunk_size

            # Try to break at sentence boundaries
            if end < len(content):
                # Look for sentence boundary within next 100 chars
                sentence_end = content.find(". ", end, min(end + 100, len(content)))
                if sentence_end != -1:
                    end = sentence_end + 1

            chunk = content[start:end].strip()
            if chunk:
                chunks.append(chunk)

            # Move start position with overlap
            start = end - chunk_overlap
            if start >= len(content):
                break

        return chunks

    async def get_knowledge_contents(
        self,
        agent_id: uuid.UUID,
        content_type: Optional[ContentType] = None,
        status: Optional[ContentStatus] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[KnowledgeContent]:
        """Get knowledge contents for an agent"""
        return await self.repository.get_knowledge_contents(
            agent_id=agent_id,
            content_type=content_type,
            status=status,
            skip=skip,
            limit=limit,
        )

    async def search_content_semantic(
        self,
        agent_id: uuid.UUID,
        query: str,
        similarity_threshold: float = 0.8,
        limit: int = 10,
        content_type: Optional[ContentType] = None,
    ) -> List[Tuple[KnowledgeChunk, KnowledgeContent, float]]:
        """Search content chunks using semantic similarity - Agentic RAG pattern"""
        query_embedding = await self._generate_embedding(query)

        results = await self.repository.search_chunks_by_similarity(
            agent_id=agent_id,
            embedding=query_embedding,
            similarity_threshold=similarity_threshold,
            limit=limit,
            content_type=content_type,
        )

        # Emit search event
        await self.event_bus.emit(
            KnowledgeEvent.knowledge_searched(
                agent_id=str(agent_id), query=query, results_count=len(results)
            )
        )

        return results

    async def delete_knowledge_content(self, content_id: uuid.UUID) -> bool:
        """Delete knowledge content and all its chunks"""
        return await self.repository.delete_knowledge_content(content_id)
