import uuid
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


# Knowledge Schemas


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


# Knowledge Content Schemas


class KnowledgeContentCreate(BaseModel):
    """Request to create knowledge content"""

    name: str = Field(..., description="Content name")
    description: Optional[str] = Field(None, description="Content description")
    content_type: str = Field(..., description="Type of content")
    content_text: Optional[str] = Field(None, description="Text content")
    file_path: Optional[str] = Field(None, description="File path")
    chunk_size: int = Field(default=1000, description="Chunk size for processing")
    chunk_overlap: int = Field(default=200, description="Overlap between chunks")
    generate_embeddings: bool = Field(
        default=True, description="Generate embeddings for chunks"
    )


class KnowledgeContentResponse(BaseModel):
    """Knowledge content response"""

    model_config = {"from_attributes": True}

    id: str = Field(..., description="Content ID")
    agent_id: str = Field(..., description="Agent ID")
    name: str = Field(..., description="Content name")
    description: Optional[str] = Field(None, description="Content description")
    content_type: str = Field(..., description="Content type")
    status: str = Field(..., description="Processing status")
    file_size: Optional[int] = Field(None, description="File size in bytes")
    chunk_size: int = Field(..., description="Chunk size")
    chunk_overlap: int = Field(..., description="Chunk overlap")
    total_chunks: int = Field(..., description="Total number of chunks")
    access_count: int = Field(..., description="Access count")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Update timestamp")


class KnowledgeContentUpdate(BaseModel):
    """Request to update knowledge content"""

    name: Optional[str] = Field(None, description="Content name")
    description: Optional[str] = Field(None, description="Content description")


class KnowledgeContentListResponse(BaseModel):
    """Response with list of knowledge content"""

    contents: List[KnowledgeContentResponse] = Field(..., description="List of content")
    total: int = Field(..., description="Total count")
    skip: int = Field(..., description="Skipped items")
    limit: int = Field(..., description="Limit applied")


class KnowledgeChunkResponse(BaseModel):
    """Knowledge chunk response"""

    model_config = {"from_attributes": True}

    id: str = Field(..., description="Chunk ID")
    content_id: str = Field(..., description="Content ID")
    chunk_text: str = Field(..., description="Chunk text")
    chunk_index: int = Field(..., description="Chunk index")
    keywords: Optional[List[str]] = Field(None, description="Chunk keywords")
    summary: Optional[str] = Field(None, description="Chunk summary")
    start_position: Optional[int] = Field(None, description="Start position in content")
    end_position: Optional[int] = Field(None, description="End position in content")


class ContentSearchRequest(BaseModel):
    """Request to search content chunks"""

    query: str = Field(..., description="Search query")
    similarity_threshold: float = Field(
        default=0.8, description="Similarity threshold", ge=0.0, le=1.0
    )
    limit: int = Field(default=10, description="Maximum results", ge=1, le=100)
    content_type: Optional[str] = Field(None, description="Filter by content type")


class ContentSearchResult(BaseModel):
    """Single content search result"""

    chunk: KnowledgeChunkResponse = Field(..., description="The chunk")
    content: KnowledgeContentResponse = Field(..., description="The content metadata")
    similarity: float = Field(..., description="Similarity score")


class ContentSearchResponse(BaseModel):
    """Response with content search results"""

    results: List[ContentSearchResult] = Field(..., description="Search results")
    query: str = Field(..., description="Original query")
    total_results: int = Field(..., description="Total number of results")


class ContentProcessingStatus(BaseModel):
    """Content processing status response"""

    content_id: str = Field(..., description="Content ID")
    status: str = Field(..., description="Processing status")
    progress: float = Field(..., description="Processing progress (0-1)")
    chunks_processed: int = Field(..., description="Number of chunks processed")
    total_chunks: int = Field(..., description="Total chunks to process")
    error_message: Optional[str] = Field(None, description="Error message if failed")
