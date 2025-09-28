"""
Semantic cache infrastructure for agent responses.

Following CLAUDE.md: Simple, boring infrastructure. Clean public API.
"""

from app.infrastructure.cache.service import SemanticCacheService
from app.infrastructure.cache.types import (
    CacheConfig,
    CacheEntry,
    CacheResult,
    CacheSearchResult,
)


__all__ = [
    "SemanticCacheService",
    "CacheEntry",
    "CacheSearchResult",
    "CacheResult",
    "CacheConfig",
]
