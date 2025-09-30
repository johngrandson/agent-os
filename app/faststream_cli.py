"""
FastStream CLI entry point for horizontal scaling.

Usage:
    faststream run app.faststream_cli:app --workers 4
    faststream run app.faststream_cli:app --reload  # Development
"""

import logging
import sys

from app.domains.agent_management.events.subscribers import AGENT_EVENTS
from app.domains.communication.messages.subscribers import MESSAGE_EVENTS
from app.domains.knowledge_base.events.subscribers import EVALUATION_EVENTS
from app.shared.events.builder import FastStreamAppBuilder
from core.logging_config import WorkerIdFilter, WorkerIdFormatter


# Configure worker ID in logs
def setup_worker_logging() -> None:
    """Add worker ID to all log handlers and suppress httpx cleanup errors"""
    root_logger = logging.getLogger()

    # Ensure we have at least one handler
    if not root_logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        root_logger.addHandler(handler)
        root_logger.setLevel(logging.INFO)

    worker_filter = WorkerIdFilter()

    # Add filter and formatter to all existing handlers
    for handler in root_logger.handlers:  # type: ignore[assignment]
        handler.addFilter(worker_filter)
        # Use WorkerIdFormatter for conditional worker ID display
        handler.setFormatter(
            WorkerIdFormatter(
                "%(asctime)s%(worker_prefix)s - %(name)s - %(levelname)s - %(message)s"
            )
        )

    # Suppress asyncio transport cleanup errors from httpx/Agno library
    # These are benign errors that occur after successful operations
    asyncio_logger = logging.getLogger("asyncio")
    asyncio_logger.addFilter(lambda record: "TCPTransport" not in str(record.getMessage()))


# Setup logging before building app
setup_worker_logging()

# Build FastStream app using declarative registry pattern
app = (
    FastStreamAppBuilder()
    .add_domain_registry(AGENT_EVENTS)
    .add_domain_registry(MESSAGE_EVENTS)
    .add_domain_registry(EVALUATION_EVENTS)
    .build()
)
