"""
Simple cache types and data structures.

Following CLAUDE.md: Essential types only, no premature abstractions.
"""

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class CacheResult(StrEnum):
    """Cache operation results."""

    HIT = "hit"
    MISS = "miss"
    ERROR = "error"


@dataclass
class CacheEntry:
    """Cache entry data structure."""

    key: str
    response: str
    embedding: list[float]
    metadata: dict[str, Any]
    ttl_seconds: int | None = None


@dataclass
class CacheSearchResult:
    """Result of cache search operation."""

    result: CacheResult
    entry: CacheEntry | None = None
    similarity_score: float | None = None
    error: str | None = None


@dataclass
class CacheConfig:
    """Cache configuration settings."""

    enabled: bool = True
    similarity_threshold: float = 0.85
    default_ttl: int = 3600
    embedding_model: str = "text-embedding-3-small"
    backend: str = "memory"
