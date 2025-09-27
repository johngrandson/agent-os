"""Tests for the centralized logger utility."""

import logging
from unittest.mock import patch

import pytest
from core.logger import (
    get_class_logger,
    get_logger,
    get_module_logger,
    setup_logging,
)


class TestLoggerUtility:
    """Test the centralized logger utility functions."""

    def test_get_logger_returns_logger_instance(self):
        """Test that get_logger returns a Logger instance."""
        logger = get_logger("test")
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test"

    def test_get_logger_with_none_returns_root(self):
        """Test that get_logger with None returns root logger."""
        logger = get_logger(None)
        assert isinstance(logger, logging.Logger)
        assert logger.name == "root"

    def test_get_module_logger_returns_logger_with_module_name(self):
        """Test that get_module_logger returns logger with correct name."""
        module_name = "app.services.test_service"
        logger = get_module_logger(module_name)
        assert isinstance(logger, logging.Logger)
        assert logger.name == module_name

    def test_get_class_logger_returns_logger_with_class_path(self):
        """Test that get_class_logger returns logger with class path."""

        class TestClass:
            pass

        logger = get_class_logger(TestClass)
        assert isinstance(logger, logging.Logger)
        expected_name = f"{TestClass.__module__}.{TestClass.__name__}"
        assert logger.name == expected_name

    @patch("core.logger.configure_logging")
    def test_setup_logging_calls_configure_logging(self, mock_configure):
        """Test that setup_logging calls the underlying configure_logging."""
        setup_logging(debug=True)
        mock_configure.assert_called_once_with(debug=True)

    def test_loggers_are_same_instance_for_same_name(self):
        """Test that multiple calls with same name return same logger."""
        logger1 = get_logger("test.module")
        logger2 = get_logger("test.module")
        assert logger1 is logger2

    def test_module_logger_same_as_get_logger(self):
        """Test that get_module_logger and get_logger return same instance."""
        name = "test.module"
        logger1 = get_logger(name)
        logger2 = get_module_logger(name)
        assert logger1 is logger2
