"""
Centralized logging utility for the application.

This module provides a simple, consistent interface for logging across the entire
application. It wraps the existing logging configuration to ensure all modules
use the same logging setup.

Following CLAUDE.md principles:
- Boring over clever: Simple wrapper around standard logging
- Single responsibility: Just provide logger instances
- Consistent patterns: Maintains existing __name__ usage
"""

import logging

from core.logging_config import configure_logging


def get_logger(name: str | None = None) -> logging.Logger:
    """
    Get a configured logger instance.

    Args:
        name: Logger name. If None, returns root logger.

    Returns:
        Configured logger instance.

    Example:
        logger = get_logger(__name__)
        logger.info("This is a log message")
    """
    return logging.getLogger(name)


def get_module_logger(module_name: str) -> logging.Logger:
    """
    Get a logger for a specific module.

    This is the preferred way to get module-specific loggers.

    Args:
        module_name: Usually __name__ from the calling module

    Returns:
        Configured logger instance for the module

    Example:
        logger = get_module_logger(__name__)
        logger.info("Module-specific log message")
    """
    return logging.getLogger(module_name)


def get_class_logger(cls) -> logging.Logger:
    """
    Get a logger for a specific class.

    Useful for class-based logging where you want to include
    both module and class name in the logger hierarchy.

    Args:
        cls: The class to get a logger for

    Returns:
        Configured logger instance for the class

    Example:
        class MyService:
            def __init__(self):
                self.logger = get_class_logger(self.__class__)
                self.logger.info("Service initialized")
    """
    return logging.getLogger(f"{cls.__module__}.{cls.__name__}")


# For backward compatibility and convenience
def setup_logging(debug: bool = False) -> None:
    """
    Configure logging for the application.

    This is a convenience wrapper around the existing configure_logging function.
    Usually called once at application startup.

    Args:
        debug: If True, enables debug level logging
    """
    configure_logging(debug=debug)


# Common logger instances that can be imported directly for convenience
app_logger = get_logger("app")
events_logger = get_logger("app.events")
providers_logger = get_logger("app.providers")
services_logger = get_logger("app.services")
