import uuid
from typing import List, Optional
from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, HTTPException, Query

from app.container import ApplicationContainer as Container
from app.knowledge.api.schemas import (
    AddContentRequest,
    AddContentResponse,
    SearchKnowledgeRequest,
    SearchKnowledgeResponse,
    KnowledgeContentResponse,
    DeleteContentResponse,
    # Enhanced schemas
    AgentMemoryCreate,
    AgentMemoryResponse,
    MemorySearchRequest,
    MemorySearchResponse,
    MemoriesListResponse,
    KnowledgeContextCreate,
    KnowledgeContextResponse,
    KnowledgeContextsListResponse,
    SearchHistoryListResponse,
)
from app.knowledge.services.knowledge_service import KnowledgeService
from app.knowledge.knowledge import MemoryType, MemoryPriority, KnowledgeSource

knowledge_router = APIRouter()


@knowledge_router.post(
    "/{agent_id}/knowledge/content",
    response_model=AddContentResponse,
    status_code=201,
    summary="Add knowledge content to agent",
    description="Add new knowledge content to an agent's knowledge base with automatic chunking and embedding generation.",
)
@inject
async def add_content(
    agent_id: str,
    request: AddContentRequest,
    knowledge_service: KnowledgeService = Depends(Provide[Container.knowledge_service]),
):
    """Add content to agent's knowledge base"""
    try:
        content = await knowledge_service.add_content(
            agent_id=agent_id,
            name=request.name,
            content=request.content,
            description=request.description,
        )
        return AddContentResponse(
            id=str(content.id), name=content.name, agent_id=content.agent_id
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add content: {str(e)}")


@knowledge_router.post(
    "/{agent_id}/knowledge/search",
    response_model=SearchKnowledgeResponse,
    summary="Search agent's knowledge",
    description="Search an agent's knowledge base using vector similarity search.",
)
@inject
async def search_knowledge(
    agent_id: str,
    request: SearchKnowledgeRequest,
    knowledge_service: KnowledgeService = Depends(Provide[Container.knowledge_service]),
):
    """Search agent's knowledge base"""
    try:
        results = await knowledge_service.search_knowledge(
            agent_id=agent_id,
            query=request.query,
            limit=request.limit,
            threshold=request.threshold,
        )
        return SearchKnowledgeResponse(results=results, query=request.query)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@knowledge_router.get(
    "/{agent_id}/knowledge/contents",
    response_model=List[KnowledgeContentResponse],
    summary="Get agent's knowledge contents",
    description="Retrieve all knowledge contents for an agent with metadata.",
)
@inject
async def get_knowledge_contents(
    agent_id: str,
    limit: int = 10,
    knowledge_service: KnowledgeService = Depends(Provide[Container.knowledge_service]),
):
    """Get all knowledge contents for an agent"""
    try:
        contents = await knowledge_service.get_agent_knowledge_contents(
            agent_id=agent_id, limit=limit
        )
        return [
            KnowledgeContentResponse(
                id=str(content.id),
                name=content.name,
                description=content.description,
                content_type=content.content_type,
                access_count=content.access_count,
                created_at=content.created_at.isoformat(),
            )
            for content in contents
        ]
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve contents: {str(e)}"
        )


@knowledge_router.delete(
    "/knowledge/content/{content_id}",
    response_model=DeleteContentResponse,
    summary="Delete knowledge content",
    description="Delete a specific knowledge content and all associated vectors.",
)
@inject
async def delete_content(
    content_id: str,
    knowledge_service: KnowledgeService = Depends(Provide[Container.knowledge_service]),
):
    """Delete knowledge content"""
    try:
        content_uuid = uuid.UUID(content_id)
        success = await knowledge_service.delete_content(content_uuid)

        if success:
            return DeleteContentResponse(
                success=True, message="Content deleted successfully"
            )
        else:
            raise HTTPException(status_code=404, detail="Content not found")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid content ID format")
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to delete content: {str(e)}"
        )


# Enhanced Knowledge Endpoints


@knowledge_router.post(
    "/{agent_id}/memories",
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

        related_task_id = (
            uuid.UUID(memory_data.related_task_id)
            if memory_data.related_task_id
            else None
        )

        memory = await knowledge_service.create_agent_memory(
            agent_id=agent_uuid,
            content=memory_data.content,
            memory_type=memory_type,
            source=source,
            summary=memory_data.summary,
            keywords=memory_data.keywords,
            priority=priority,
            context_data=memory_data.context_data,
            related_task_id=related_task_id,
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
    "/{agent_id}/memories",
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
    "/{agent_id}/memories/search",
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
    "/{agent_id}/memories/{memory_id}/archive",
    status_code=204,
    summary="Archive agent memory",
    description="Archive an agent memory",
)
@inject
async def archive_agent_memory(
    agent_id: str,
    memory_id: str,
    knowledge_service: KnowledgeService = Depends(Provide[Container.knowledge_service]),
):
    """Archive an agent memory"""
    try:
        memory_uuid = uuid.UUID(memory_id)
        success = await knowledge_service.archive_memory(memory_uuid)
        if not success:
            raise HTTPException(status_code=404, detail="Memory not found")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid memory ID format")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to archive memory: {str(e)}"
        )


@knowledge_router.post(
    "/{agent_id}/contexts",
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
    "/{agent_id}/contexts",
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


@knowledge_router.get(
    "/search-history",
    response_model=SearchHistoryListResponse,
    summary="Get search history",
    description="Get semantic search history",
)
@inject
async def get_search_history(
    agent_id: Optional[str] = Query(None, description="Filter by agent ID"),
    search_type: Optional[str] = Query(None, description="Filter by search type"),
    session_id: Optional[str] = Query(None, description="Filter by session ID"),
    skip: int = Query(0, ge=0, description="Number of searches to skip"),
    limit: int = Query(
        50, ge=1, le=500, description="Maximum number of searches to return"
    ),
    knowledge_service: KnowledgeService = Depends(Provide[Container.knowledge_service]),
):
    """Get semantic search history"""
    try:
        agent_uuid = uuid.UUID(agent_id) if agent_id else None
        session_uuid = uuid.UUID(session_id) if session_id else None

        searches = await knowledge_service.get_search_history(
            agent_id=agent_uuid,
            search_type=search_type,
            session_id=session_uuid,
            skip=skip,
            limit=limit,
        )

        search_responses = [
            {
                "id": str(search.id),
                "query": search.query,
                "search_type": search.search_type,
                "results_count": search.results_count,
                "execution_time": search.execution_time,
                "created_at": search.created_at.isoformat()
                if hasattr(search.created_at, "isoformat")
                else str(search.created_at),
            }
            for search in searches
        ]
        return SearchHistoryListResponse(
            searches=search_responses,
            total=len(search_responses),
            skip=skip,
            limit=limit,
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ID format")
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get search history: {str(e)}"
        )
