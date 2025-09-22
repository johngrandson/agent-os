"""
Logging configuration for the application
"""

import logging
import sys
from typing import Dict, Any


def setup_logging(level: str = "INFO") -> Dict[str, Any]:
    """Setup logging configuration for the application"""

    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
            "detailed": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(funcName)s:%(lineno)d - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": level,
                "formatter": "default",
                "stream": "ext://sys.stdout",
            },
            "detailed_console": {
                "class": "logging.StreamHandler",
                "level": "DEBUG",
                "formatter": "detailed",
                "stream": "ext://sys.stdout",
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
            "app.workflows": {
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

    return config


def configure_logging(debug: bool = False) -> None:
    """Configure logging for the application"""
    import logging.config

    level = "DEBUG" if debug else "INFO"
    config = setup_logging(level)

    # Apply the configuration
    logging.config.dictConfig(config)

    # Ensure uvicorn logs are visible
    uvicorn_logger = logging.getLogger("uvicorn")
    uvicorn_logger.setLevel(logging.INFO)

    uvicorn_access = logging.getLogger("uvicorn.access")
    uvicorn_access.setLevel(logging.INFO)

    # Set up root logger to output to stdout
    root_logger = logging.getLogger()
    if not root_logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
        root_logger.addHandler(handler)

    logging.info(f"Logging configured with level: {level}")
