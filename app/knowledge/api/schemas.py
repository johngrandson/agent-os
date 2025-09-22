import uuid
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class AddContentRequest(BaseModel):
    """Request to add knowledge content"""

    name: str = Field(..., description="Name of the knowledge content")
    content: str = Field(..., description="The actual content to be stored")
    description: Optional[str] = Field(None, description="Description of the content")


class AddContentResponse(BaseModel):
    """Response after adding knowledge content"""

    id: str = Field(..., description="Content ID")
    name: str = Field(..., description="Content name")
    agent_id: str = Field(..., description="Agent ID")


class SearchKnowledgeRequest(BaseModel):
    """Request to search knowledge"""

    query: str = Field(..., description="Search query")
    limit: int = Field(default=5, description="Maximum number of results", ge=1, le=20)
    threshold: float = Field(
        default=0.7, description="Similarity threshold", ge=0.0, le=1.0
    )


class SearchKnowledgeResponse(BaseModel):
    """Response with search results"""

    results: List[str] = Field(..., description="List of relevant content chunks")
    query: str = Field(..., description="Original search query")


class KnowledgeContentResponse(BaseModel):
    """Knowledge content information"""

    model_config = {"from_attributes": True}

    id: str = Field(..., description="Content ID")
    name: str = Field(..., description="Content name")
    description: Optional[str] = Field(None, description="Content description")
    content_type: str = Field(..., description="Type of content")
    access_count: int = Field(..., description="Number of times accessed")
    created_at: str = Field(..., description="Creation timestamp")


class DeleteContentResponse(BaseModel):
    """Response after deleting content"""

    success: bool = Field(..., description="Whether deletion was successful")
    message: str = Field(..., description="Status message")


# Enhanced Knowledge Schemas


class AgentMemoryCreate(BaseModel):
    """Request to create agent memory"""

    content: str = Field(..., description="Memory content")
    memory_type: str = Field(..., description="Type of memory")
    source: str = Field(..., description="Source of the memory")
    summary: Optional[str] = Field(None, description="Summary of the memory")
    keywords: Optional[List[str]] = Field(None, description="Keywords for the memory")
    priority: str = Field(default="medium", description="Priority level")
    context_data: Optional[Dict[str, Any]] = Field(
        None, description="Additional context data"
    )
    related_task_id: Optional[str] = Field(None, description="Related task ID")
    retention_days: Optional[int] = Field(None, description="Days to retain the memory")
    generate_embedding: bool = Field(
        default=True, description="Generate vector embedding"
    )


class AgentMemoryResponse(BaseModel):
    """Agent memory response"""

    model_config = {"from_attributes": True}

    id: str = Field(..., description="Memory ID")
    agent_id: str = Field(..., description="Agent ID")
    content: str = Field(..., description="Memory content")
    summary: Optional[str] = Field(None, description="Memory summary")
    keywords: Optional[List[str]] = Field(None, description="Memory keywords")
    memory_type: str = Field(..., description="Type of memory")
    priority: str = Field(..., description="Priority level")
    source: str = Field(..., description="Source of the memory")
    context_data: Optional[Dict[str, Any]] = Field(None, description="Context data")
    access_count: int = Field(..., description="Access count")
    is_archived: bool = Field(..., description="Whether memory is archived")
    created_at: str = Field(..., description="Creation timestamp")


class MemorySearchRequest(BaseModel):
    """Request to search memories"""

    query: str = Field(..., description="Search query")
    similarity_threshold: float = Field(
        default=0.8, description="Similarity threshold", ge=0.0, le=1.0
    )
    limit: int = Field(default=10, description="Maximum results", ge=1, le=100)
    memory_type: Optional[str] = Field(None, description="Filter by memory type")


class MemorySearchResult(BaseModel):
    """Single memory search result"""

    memory: AgentMemoryResponse = Field(..., description="The memory")
    similarity: float = Field(..., description="Similarity score")


class MemorySearchResponse(BaseModel):
    """Response with memory search results"""

    results: List[MemorySearchResult] = Field(..., description="Search results")
    query: str = Field(..., description="Original query")
    total_results: int = Field(..., description="Total number of results")


class MemoriesListResponse(BaseModel):
    """Response with list of memories"""

    memories: List[AgentMemoryResponse] = Field(..., description="List of memories")
    total: int = Field(..., description="Total count")
    skip: int = Field(..., description="Skipped items")
    limit: int = Field(..., description="Limit applied")


class KnowledgeContextCreate(BaseModel):
    """Request to create knowledge context"""

    context_type: str = Field(..., description="Type of context")
    context_key: str = Field(..., description="Context key")
    context_value: Dict[str, Any] = Field(..., description="Context value")
    priority: int = Field(default=5, description="Priority level")
    expiry: Optional[str] = Field(None, description="Expiry timestamp")
    generate_embedding: bool = Field(
        default=True, description="Generate vector embedding"
    )


class KnowledgeContextResponse(BaseModel):
    """Knowledge context response"""

    model_config = {"from_attributes": True}

    id: str = Field(..., description="Context ID")
    agent_id: str = Field(..., description="Agent ID")
    context_type: str = Field(..., description="Context type")
    context_key: str = Field(..., description="Context key")
    context_value: Dict[str, Any] = Field(..., description="Context value")
    priority: int = Field(..., description="Priority level")
    is_active: bool = Field(..., description="Whether context is active")
    usage_count: int = Field(..., description="Usage count")
    created_at: str = Field(..., description="Creation timestamp")


class KnowledgeContextsListResponse(BaseModel):
    """Response with list of knowledge contexts"""

    contexts: List[KnowledgeContextResponse] = Field(
        ..., description="List of contexts"
    )
    total: int = Field(..., description="Total count")
    skip: int = Field(..., description="Skipped items")
    limit: int = Field(..., description="Limit applied")


class SemanticSearchResponse(BaseModel):
    """Semantic search response"""

    model_config = {"from_attributes": True}

    id: str = Field(..., description="Search ID")
    query: str = Field(..., description="Search query")
    search_type: str = Field(..., description="Search type")
    results_count: int = Field(..., description="Number of results")
    execution_time: Optional[float] = Field(None, description="Execution time")
    created_at: str = Field(..., description="Creation timestamp")


class SearchHistoryListResponse(BaseModel):
    """Response with search history"""

    searches: List[SemanticSearchResponse] = Field(..., description="List of searches")
    total: int = Field(..., description="Total count")
    skip: int = Field(..., description="Skipped items")
    limit: int = Field(..., description="Limit applied")
