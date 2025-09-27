#!/usr/bin/env python3
"""
Demonstration of the centralized logging system.

This file shows how to use the new centralized logging utility
and compares it with the old direct logging approach.
"""

# Set up logging configuration first
from core.logger import setup_logging
setup_logging(debug=False)

# New centralized approach
from core.logger import get_module_logger, get_class_logger, get_logger

# Get a module-specific logger (preferred approach)
logger = get_module_logger(__name__)


class ExampleService:
    """Example service demonstrating class-based logging."""

    def __init__(self):
        # Class-specific logger includes both module and class name
        self.logger = get_class_logger(self.__class__)
        self.logger.info("ExampleService initialized")

    def process_data(self, data: str) -> str:
        """Process some data with logging."""
        self.logger.debug(f"Processing data: {data}")

        if not data:
            self.logger.warning("Empty data received")
            return "processed: empty"

        if data == "error":
            self.logger.error("Error condition detected in data")
            return "processed: error"

        self.logger.info(f"Successfully processed data: {data}")
        return f"processed: {data}"


def demonstrate_logging():
    """Demonstrate different logging approaches."""

    # Module-level logging
    logger.info("Starting logging demonstration")

    # Service with class-based logging
    service = ExampleService()

    # Test different log levels
    test_data = ["hello", "", "error", "world"]

    for data in test_data:
        result = service.process_data(data)
        logger.debug(f"Result: {result}")

    # Direct logger usage for specific purposes
    performance_logger = get_logger("app.performance")
    performance_logger.info("Operation completed in 0.05s")

    # Event-specific logger
    event_logger = get_logger("app.events.demo")
    event_logger.info("Demo event completed")

    logger.info("Logging demonstration completed")


if __name__ == "__main__":
    demonstrate_logging()
