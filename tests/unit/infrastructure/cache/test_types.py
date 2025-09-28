"""
Tests for cache types and data structures.

Following CLAUDE.md: Simple tests for simple types.
"""

import pytest
from app.infrastructure.cache.types import CacheEntry, CacheResult


class TestCacheEntry:
    """Test cache entry data structure"""

    def test_cache_entry_creation(self):
        """Should create cache entry with required fields"""
        # Execute
        entry = CacheEntry(
            key="test_key",
            response="test response",
            embedding=[0.1, 0.2, 0.3],
            metadata={"agent_id": "123"},
        )

        # Assert
        assert entry.key == "test_key"
        assert entry.response == "test response"
        assert entry.embedding == [0.1, 0.2, 0.3]
        assert entry.metadata == {"agent_id": "123"}
        assert entry.ttl_seconds is None  # Default value

    def test_cache_entry_with_ttl(self):
        """Should create cache entry with TTL"""
        # Execute
        entry = CacheEntry(
            key="test_key",
            response="test response",
            embedding=[0.1, 0.2, 0.3],
            metadata={},
            ttl_seconds=3600,
        )

        # Assert
        assert entry.ttl_seconds == 3600

    def test_cache_entry_equality(self):
        """Cache entries should be equal if all fields match"""
        # Setup
        entry1 = CacheEntry(
            key="key1", response="response1", embedding=[0.1, 0.2], metadata={"test": "value"}
        )
        entry2 = CacheEntry(
            key="key1", response="response1", embedding=[0.1, 0.2], metadata={"test": "value"}
        )

        # Assert
        assert entry1 == entry2

    def test_cache_entry_inequality(self):
        """Cache entries should not be equal if fields differ"""
        # Setup
        entry1 = CacheEntry(key="key1", response="response1", embedding=[0.1, 0.2], metadata={})
        entry2 = CacheEntry(
            key="key2",  # Different key
            response="response1",
            embedding=[0.1, 0.2],
            metadata={},
        )

        # Assert
        assert entry1 != entry2


class TestCacheResult:
    """Test cache result enum"""

    def test_cache_result_values(self):
        """Should have correct enum values"""
        assert CacheResult.HIT == "hit"
        assert CacheResult.MISS == "miss"
        assert CacheResult.ERROR == "error"

    def test_cache_result_comparison(self):
        """Should compare cache results correctly"""
        assert CacheResult.HIT == CacheResult.HIT
        assert CacheResult.HIT != CacheResult.MISS
        assert CacheResult.MISS != CacheResult.ERROR
