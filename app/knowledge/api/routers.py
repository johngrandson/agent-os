import uuid
from typing import Optional
from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, HTTPException, Query

from app.container import ApplicationContainer as Container
from app.knowledge.api.schemas import (
    AgentMemoryCreate,
    AgentMemoryResponse,
    MemorySearchRequest,
    MemorySearchResponse,
    MemoriesListResponse,
    KnowledgeContextCreate,
    KnowledgeContextResponse,
    KnowledgeContextsListResponse,
    KnowledgeContentCreate,
    KnowledgeContentResponse,
    KnowledgeContentUpdate,
    KnowledgeContentListResponse,
    KnowledgeChunkResponse,
    ContentSearchRequest,
    ContentSearchResponse,
    ContentProcessingStatus,
)
from app.knowledge.services.knowledge_service import KnowledgeService
from app.knowledge.knowledge import (
    MemoryType,
    MemoryPriority,
    KnowledgeSource,
    ContentType,
    ContentStatus,
)

knowledge_router = APIRouter()


@knowledge_router.post(
    "/knowledge/{agent_id}/memories",
    response_model=AgentMemoryResponse,
    status_code=201,
    summary="Create agent memory",
    description="Create a new agent memory with optional embedding generation",
)
@inject
async def create_agent_memory(
    agent_id: str,
    memory_data: AgentMemoryCreate,
    knowledge_service: KnowledgeService = Depends(Provide[Container.knowledge_service]),
):
    """Create a new agent memory"""
    try:
        agent_uuid = uuid.UUID(agent_id)
        memory_type = MemoryType(memory_data.memory_type)
        priority = MemoryPriority(memory_data.priority)
        source = KnowledgeSource(memory_data.source)

        memory = await knowledge_service.create_agent_memory(
            agent_id=agent_uuid,
            content=memory_data.content,
            memory_type=memory_type,
            source=source,
            summary=memory_data.summary,
            keywords=memory_data.keywords,
            priority=priority,
            context_data=memory_data.context_data,
            retention_days=memory_data.retention_days,
            generate_embedding=memory_data.generate_embedding,
        )

        return AgentMemoryResponse.model_validate(memory)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to create memory: {str(e)}"
        )


@knowledge_router.get(
    "/knowledge/{agent_id}/memories",
    response_model=MemoriesListResponse,
    summary="Get agent memories",
    description="Get agent memories with optional filtering",
)
@inject
async def get_agent_memories(
    agent_id: str,
    memory_type: Optional[str] = Query(None, description="Filter by memory type"),
    priority: Optional[str] = Query(None, description="Filter by priority"),
    source: Optional[str] = Query(None, description="Filter by source"),
    skip: int = Query(0, ge=0, description="Number of memories to skip"),
    limit: int = Query(
        100, ge=1, le=1000, description="Maximum number of memories to return"
    ),
    knowledge_service: KnowledgeService = Depends(Provide[Container.knowledge_service]),
):
    """Get agent memories with optional filtering"""
    try:
        agent_uuid = uuid.UUID(agent_id)
        memory_type_enum = MemoryType(memory_type) if memory_type else None
        priority_enum = MemoryPriority(priority) if priority else None
        source_enum = KnowledgeSource(source) if source else None

        memories = await knowledge_service.get_agent_memories(
            agent_id=agent_uuid,
            memory_type=memory_type_enum,
            priority=priority_enum,
            source=source_enum,
            skip=skip,
            limit=limit,
        )

        memory_responses = [
            AgentMemoryResponse.model_validate(memory) for memory in memories
        ]
        return MemoriesListResponse(
            memories=memory_responses,
            total=len(memory_responses),
            skip=skip,
            limit=limit,
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid agent ID or filter values")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get memories: {str(e)}")


@knowledge_router.post(
    "/knowledge/{agent_id}/memories/search",
    response_model=MemorySearchResponse,
    summary="Search agent memories",
    description="Search agent memories using semantic similarity",
)
@inject
async def search_agent_memories(
    agent_id: str,
    search_request: MemorySearchRequest,
    knowledge_service: KnowledgeService = Depends(Provide[Container.knowledge_service]),
):
    """Search agent memories using semantic similarity"""
    try:
        agent_uuid = uuid.UUID(agent_id)
        memory_type_enum = (
            MemoryType(search_request.memory_type)
            if search_request.memory_type
            else None
        )

        results = await knowledge_service.search_memories_semantic(
            agent_id=agent_uuid,
            query=search_request.query,
            similarity_threshold=search_request.similarity_threshold,
            limit=search_request.limit,
            memory_type=memory_type_enum,
        )

        search_results = [
            {
                "memory": AgentMemoryResponse.model_validate(memory),
                "similarity": similarity,
            }
            for memory, similarity in results
        ]

        return MemorySearchResponse(
            results=search_results,
            query=search_request.query,
            total_results=len(search_results),
        )
    except ValueError:
        raise HTTPException(
            status_code=400, detail="Invalid agent ID or search parameters"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to search memories: {str(e)}"
        )


@knowledge_router.post(
    "/knowledge/{agent_id}/contexts",
    response_model=KnowledgeContextResponse,
    status_code=201,
    summary="Create knowledge context",
    description="Create a knowledge context for an agent",
)
@inject
async def create_knowledge_context(
    agent_id: str,
    context_data: KnowledgeContextCreate,
    knowledge_service: KnowledgeService = Depends(Provide[Container.knowledge_service]),
):
    """Create a knowledge context for an agent"""
    try:
        agent_uuid = uuid.UUID(agent_id)

        context = await knowledge_service.create_knowledge_context(
            agent_id=agent_uuid,
            context_type=context_data.context_type,
            context_key=context_data.context_key,
            context_value=context_data.context_value,
            priority=context_data.priority,
            expiry=context_data.expiry,
            generate_embedding=context_data.generate_embedding,
        )

        return KnowledgeContextResponse.model_validate(context)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid agent ID format")
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to create knowledge context: {str(e)}"
        )


@knowledge_router.get(
    "/knowledge/{agent_id}/contexts",
    response_model=KnowledgeContextsListResponse,
    summary="Get knowledge contexts",
    description="Get knowledge contexts for an agent",
)
@inject
async def get_knowledge_contexts(
    agent_id: str,
    context_type: Optional[str] = Query(None, description="Filter by context type"),
    is_active: bool = Query(True, description="Filter by active status"),
    skip: int = Query(0, ge=0, description="Number of contexts to skip"),
    limit: int = Query(
        100, ge=1, le=1000, description="Maximum number of contexts to return"
    ),
    knowledge_service: KnowledgeService = Depends(Provide[Container.knowledge_service]),
):
    """Get knowledge contexts for an agent"""
    try:
        agent_uuid = uuid.UUID(agent_id)

        contexts = await knowledge_service.get_knowledge_contexts(
            agent_id=agent_uuid,
            context_type=context_type,
            is_active=is_active,
            skip=skip,
            limit=limit,
        )

        context_responses = [
            KnowledgeContextResponse.model_validate(context) for context in contexts
        ]

        return KnowledgeContextsListResponse(
            contexts=context_responses,
            total=len(context_responses),
            skip=skip,
            limit=limit,
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid agent ID format")
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get knowledge contexts: {str(e)}"
        )


# Knowledge Content Endpoints - Agno-style content management


@knowledge_router.post(
    "/knowledge/{agent_id}/content",
    response_model=KnowledgeContentResponse,
    status_code=201,
    summary="Create knowledge content",
    description="Create knowledge content for an agent (text or file-based)",
)
@inject
async def create_knowledge_content(
    agent_id: str,
    content_data: KnowledgeContentCreate,
    knowledge_service: KnowledgeService = Depends(Provide[Container.knowledge_service]),
):
    """Create knowledge content for an agent"""
    try:
        agent_uuid = uuid.UUID(agent_id)
        content_type = ContentType(content_data.content_type)

        content = await knowledge_service.create_knowledge_content(
            agent_id=agent_uuid,
            name=content_data.name,
            content_type=content_type,
            content_text=content_data.content_text,
            file_path=content_data.file_path,
            description=content_data.description,
            chunk_size=content_data.chunk_size,
            chunk_overlap=content_data.chunk_overlap,
            generate_embeddings=content_data.generate_embeddings,
        )

        return KnowledgeContentResponse.model_validate(content)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to create knowledge content: {str(e)}"
        )


@knowledge_router.get(
    "/knowledge/{agent_id}/content",
    response_model=KnowledgeContentListResponse,
    summary="Get knowledge content",
    description="Get knowledge content for an agent with optional filtering",
)
@inject
async def get_knowledge_content(
    agent_id: str,
    content_type: Optional[str] = Query(None, description="Filter by content type"),
    status: Optional[str] = Query(None, description="Filter by processing status"),
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(
        100, ge=1, le=1000, description="Maximum number of items to return"
    ),
    knowledge_service: KnowledgeService = Depends(Provide[Container.knowledge_service]),
):
    """Get knowledge content for an agent"""
    try:
        agent_uuid = uuid.UUID(agent_id)
        content_type_enum = ContentType(content_type) if content_type else None
        status_enum = ContentStatus(status) if status else None

        contents = await knowledge_service.get_knowledge_contents(
            agent_id=agent_uuid,
            content_type=content_type_enum,
            status=status_enum,
            skip=skip,
            limit=limit,
        )

        content_responses = [
            KnowledgeContentResponse.model_validate(content) for content in contents
        ]

        return KnowledgeContentListResponse(
            contents=content_responses,
            total=len(content_responses),
            skip=skip,
            limit=limit,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get knowledge content: {str(e)}"
        )


@knowledge_router.post(
    "/knowledge/{agent_id}/content/search",
    response_model=ContentSearchResponse,
    summary="Search knowledge content",
    description="Search knowledge content using semantic similarity (Agentic RAG)",
)
@inject
async def search_knowledge_content(
    agent_id: str,
    search_request: ContentSearchRequest,
    knowledge_service: KnowledgeService = Depends(Provide[Container.knowledge_service]),
):
    """Search knowledge content using semantic similarity - Agentic RAG pattern"""
    try:
        agent_uuid = uuid.UUID(agent_id)
        content_type_enum = (
            ContentType(search_request.content_type)
            if search_request.content_type
            else None
        )

        results = await knowledge_service.search_content_semantic(
            agent_id=agent_uuid,
            query=search_request.query,
            similarity_threshold=search_request.similarity_threshold,
            limit=search_request.limit,
            content_type=content_type_enum,
        )

        search_results = [
            {
                "chunk": KnowledgeChunkResponse.model_validate(chunk),
                "content": KnowledgeContentResponse.model_validate(content),
                "similarity": similarity,
            }
            for chunk, content, similarity in results
        ]

        return ContentSearchResponse(
            results=search_results,
            query=search_request.query,
            total_results=len(search_results),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to search content: {str(e)}"
        )


@knowledge_router.get(
    "/knowledge/{agent_id}/content/{content_id}",
    response_model=KnowledgeContentResponse,
    summary="Get specific knowledge content",
    description="Get specific knowledge content by ID",
)
@inject
async def get_knowledge_content_by_id(
    agent_id: str,
    content_id: str,
    knowledge_service: KnowledgeService = Depends(Provide[Container.knowledge_service]),
):
    """Get specific knowledge content by ID"""
    try:
        agent_uuid = uuid.UUID(agent_id)
        content_uuid = uuid.UUID(content_id)

        content = await knowledge_service.repository.get_knowledge_content_by_id(
            content_uuid
        )
        if not content or content.agent_id != agent_uuid:
            raise HTTPException(status_code=404, detail="Knowledge content not found")

        return KnowledgeContentResponse.model_validate(content)
    except ValueError:
        raise HTTPException(
            status_code=400, detail="Invalid agent ID or content ID format"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get knowledge content: {str(e)}"
        )


@knowledge_router.delete(
    "/knowledge/{agent_id}/content/{content_id}",
    status_code=204,
    summary="Delete knowledge content",
    description="Delete knowledge content and all its chunks",
)
@inject
async def delete_knowledge_content(
    agent_id: str,
    content_id: str,
    knowledge_service: KnowledgeService = Depends(Provide[Container.knowledge_service]),
):
    """Delete knowledge content and all its chunks"""
    try:
        agent_uuid = uuid.UUID(agent_id)
        content_uuid = uuid.UUID(content_id)

        # Verify content belongs to agent
        content = await knowledge_service.repository.get_knowledge_content_by_id(
            content_uuid
        )
        if not content or content.agent_id != agent_uuid:
            raise HTTPException(status_code=404, detail="Knowledge content not found")

        success = await knowledge_service.delete_knowledge_content(content_uuid)
        if not success:
            raise HTTPException(status_code=404, detail="Knowledge content not found")

    except ValueError:
        raise HTTPException(
            status_code=400, detail="Invalid agent ID or content ID format"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to delete knowledge content: {str(e)}"
        )


@knowledge_router.get(
    "/knowledge/{agent_id}/content/{content_id}/chunks",
    response_model=list[KnowledgeChunkResponse],
    summary="Get content chunks",
    description="Get chunks for specific knowledge content",
)
@inject
async def get_content_chunks(
    agent_id: str,
    content_id: str,
    skip: int = Query(0, ge=0, description="Number of chunks to skip"),
    limit: int = Query(
        100, ge=1, le=1000, description="Maximum number of chunks to return"
    ),
    knowledge_service: KnowledgeService = Depends(Provide[Container.knowledge_service]),
):
    """Get chunks for specific knowledge content"""
    try:
        agent_uuid = uuid.UUID(agent_id)
        content_uuid = uuid.UUID(content_id)

        # Verify content belongs to agent
        content = await knowledge_service.repository.get_knowledge_content_by_id(
            content_uuid
        )
        if not content or content.agent_id != agent_uuid:
            raise HTTPException(status_code=404, detail="Knowledge content not found")

        chunks = await knowledge_service.repository.get_content_chunks(
            content_id=content_uuid,
            skip=skip,
            limit=limit,
        )

        return [KnowledgeChunkResponse.model_validate(chunk) for chunk in chunks]
    except ValueError:
        raise HTTPException(
            status_code=400, detail="Invalid agent ID or content ID format"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get content chunks: {str(e)}"
        )
