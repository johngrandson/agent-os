"""Simple types for semantic cache."""

from enum import StrEnum


class CacheResult(StrEnum):
    """Cache operation results."""

    HIT = "hit"
    MISS = "miss"
    ERROR = "error"
