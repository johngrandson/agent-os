"""
Integration event types
"""

from enum import Enum


class IntegrationEventType(str, Enum):
    """Types of integration-related events"""

    INTEGRATION_CREATED = "integration.created"
    INTEGRATION_UPDATED = "integration.updated"
    INTEGRATION_DELETED = "integration.deleted"
    INTEGRATION_REQUEST = "integration.request"
