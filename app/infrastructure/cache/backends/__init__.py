"""
Cache backends for semantic cache service.

Following CLAUDE.md: Simple exports, boring solution.
"""

from .base import CacheBackend
from .memory import MemoryBackend


__all__ = ["CacheBackend", "MemoryBackend"]
