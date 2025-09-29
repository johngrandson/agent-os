"""Simple semantic cache for AI queries."""

from app.infrastructure.cache.service import SemanticCacheService
from app.infrastructure.cache.types import CacheResult


__all__ = [
    "SemanticCacheService",
    "CacheResult",
]
