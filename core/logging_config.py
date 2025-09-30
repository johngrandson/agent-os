"""
Logging configuration for the application
"""

import logging
import os
import sys
from typing import Any


class WorkerIdFilter(logging.Filter):
    """Add worker ID to log records for multi-worker environments (FastStream only)"""

    def filter(self, record: logging.LogRecord) -> bool:
        # Only add worker ID if FASTSTREAM_WORKER environment variable is set
        # This ensures worker IDs only appear in FastStream workers, not FastAPI
        if os.getenv("FASTSTREAM_WORKER", "false").lower() == "true":
            worker_id = os.getenv("WORKER_ID")
            if not worker_id:
                # Fallback to process ID for identification
                pid = os.getpid()
                worker_id = f"w{pid % 1000:03d}"  # Last 3 digits of PID
            record.worker_id = worker_id
        else:
            # For non-worker processes (like FastAPI), use empty string
            record.worker_id = ""
        return True


class WorkerIdFormatter(logging.Formatter):
    """Custom formatter that only shows worker ID when present"""

    def format(self, record: logging.LogRecord) -> str:
        # Add worker_prefix attribute that includes brackets only if worker_id exists
        worker_id = getattr(record, "worker_id", "")
        if worker_id:
            record.worker_prefix = f" - [{worker_id}]"
        else:
            record.worker_prefix = ""
        return super().format(record)


def setup_logging(level: str = "INFO") -> dict[str, Any]:
    """Setup logging configuration for the application"""

    return {
        "version": 1,
        "disable_existing_loggers": False,
        "filters": {
            "worker_id": {
                "()": "core.logging_config.WorkerIdFilter",
            }
        },
        "formatters": {
            "default": {
                "()": "core.logging_config.WorkerIdFormatter",
                "fmt": "%(asctime)s%(worker_prefix)s - %(name)s - %(levelname)s - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
            "detailed": {
                "()": "core.logging_config.WorkerIdFormatter",
                "fmt": (
                    "%(asctime)s%(worker_prefix)s - %(name)s - %(levelname)s - "
                    "%(module)s:%(funcName)s:%(lineno)d - %(message)s"
                ),
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": level,
                "formatter": "default",
                "stream": "ext://sys.stdout",
                "filters": ["worker_id"],
            },
            "detailed_console": {
                "class": "logging.StreamHandler",
                "level": "DEBUG",
                "formatter": "detailed",
                "stream": "ext://sys.stdout",
                "filters": ["worker_id"],
            },
        },
        "loggers": {
            "app": {
                "level": level,
                "handlers": ["console"],
                "propagate": False,
            },
            "app.events": {
                "level": level,
                "handlers": ["console"],
                "propagate": False,
            },
            "app.initialization": {
                "level": level,
                "handlers": ["console"],
                "propagate": False,
            },
        },
        "root": {
            "level": level,
            "handlers": ["console"],
        },
    }


def configure_logging(debug: bool = False) -> None:
    """Configure logging for the application"""
    import logging.config

    level = "INFO"
    config = setup_logging(level)

    # Apply the configuration
    logging.config.dictConfig(config)

    # Ensure uvicorn logs are visible
    uvicorn_logger = logging.getLogger("uvicorn")
    uvicorn_logger.setLevel(logging.INFO)

    uvicorn_access = logging.getLogger("uvicorn.access")
    uvicorn_access.setLevel(logging.INFO)

    # Set up root logger to output to stdout with conditional worker ID
    root_logger = logging.getLogger()
    if not root_logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.addFilter(WorkerIdFilter())
        handler.setFormatter(
            WorkerIdFormatter(
                "%(asctime)s%(worker_prefix)s - %(name)s - %(levelname)s - %(message)s"
            )
        )
        root_logger.addHandler(handler)

    logging.info(f"Logging configured with level: {level}")
