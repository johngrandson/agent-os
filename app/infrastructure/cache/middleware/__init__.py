"""
AI Provider cache middleware for transparent semantic caching.

Following CLAUDE.md: Simple decorator pattern, no premature abstractions.
"""

from app.infrastructure.cache.middleware.cached_provider import CachedRuntimeAgent


__all__ = ["CachedRuntimeAgent"]
