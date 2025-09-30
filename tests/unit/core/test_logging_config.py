"""
Tests for logging configuration with worker ID support

Tests the worker logging system to ensure:
- WorkerIdFilter adds worker_id when FASTSTREAM_WORKER=true
- WorkerIdFilter sets empty worker_id when FASTSTREAM_WORKER=false
- Worker ID format is correct (e.g., "w014" based on PID)
- WorkerIdFormatter adds [w014] prefix when worker_id exists
- WorkerIdFormatter adds empty prefix when worker_id is empty
"""

import logging
import os
from unittest.mock import patch

import pytest
from core.logging_config import WorkerIdFilter, WorkerIdFormatter


class TestWorkerIdFilter:
    """Test the WorkerIdFilter for conditional worker ID logging"""

    @pytest.fixture
    def log_record(self) -> logging.LogRecord:
        """Create a test log record"""
        return logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None,
        )

    def test_should_add_worker_id_when_faststream_worker_is_true(
        self, log_record: logging.LogRecord
    ):
        """Test that worker_id is added when FASTSTREAM_WORKER=true"""
        # Arrange
        worker_filter = WorkerIdFilter()

        with patch.dict(os.environ, {"FASTSTREAM_WORKER": "true", "WORKER_ID": "w123"}):
            # Act
            result = worker_filter.filter(log_record)

            # Assert
            assert result is True
            assert hasattr(log_record, "worker_id")
            assert log_record.worker_id == "w123"

    def test_should_set_empty_worker_id_when_faststream_worker_is_false(
        self, log_record: logging.LogRecord
    ):
        """Test that worker_id is empty when FASTSTREAM_WORKER=false"""
        # Arrange
        worker_filter = WorkerIdFilter()

        with patch.dict(os.environ, {"FASTSTREAM_WORKER": "false"}, clear=True):
            # Act
            result = worker_filter.filter(log_record)

            # Assert
            assert result is True
            assert hasattr(log_record, "worker_id")
            assert log_record.worker_id == ""

    def test_should_set_empty_worker_id_when_faststream_worker_not_set(
        self, log_record: logging.LogRecord
    ):
        """Test that worker_id is empty when FASTSTREAM_WORKER env var is not set"""
        # Arrange
        worker_filter = WorkerIdFilter()

        with patch.dict(os.environ, {}, clear=True):
            # Act
            result = worker_filter.filter(log_record)

            # Assert
            assert result is True
            assert hasattr(log_record, "worker_id")
            assert log_record.worker_id == ""

    def test_should_generate_worker_id_from_pid_when_worker_id_not_set(
        self, log_record: logging.LogRecord
    ):
        """Test that worker_id is generated from PID when WORKER_ID env var is not set"""
        # Arrange
        worker_filter = WorkerIdFilter()
        test_pid = 12345

        with (
            patch.dict(os.environ, {"FASTSTREAM_WORKER": "true"}, clear=True),
            patch("os.getpid", return_value=test_pid),
        ):
            # Act
            result = worker_filter.filter(log_record)

            # Assert
            assert result is True
            assert hasattr(log_record, "worker_id")
            # PID 12345 -> 345 (last 3 digits) -> w345
            expected_worker_id = f"w{test_pid % 1000:03d}"
            assert log_record.worker_id == expected_worker_id

    def test_should_format_worker_id_with_leading_zeros(self, log_record: logging.LogRecord):
        """Test that worker_id format has 3 digits with leading zeros"""
        # Arrange
        worker_filter = WorkerIdFilter()
        test_pid = 14  # Should become w014

        with (
            patch.dict(os.environ, {"FASTSTREAM_WORKER": "true"}, clear=True),
            patch("os.getpid", return_value=test_pid),
        ):
            # Act
            result = worker_filter.filter(log_record)

            # Assert
            assert result is True
            assert log_record.worker_id == "w014"

    def test_should_handle_large_pid_values(self, log_record: logging.LogRecord):
        """Test that worker_id uses modulo for large PID values"""
        # Arrange
        worker_filter = WorkerIdFilter()
        test_pid = 123456  # Should become w456 (last 3 digits)

        with (
            patch.dict(os.environ, {"FASTSTREAM_WORKER": "true"}, clear=True),
            patch("os.getpid", return_value=test_pid),
        ):
            # Act
            result = worker_filter.filter(log_record)

            # Assert
            assert result is True
            assert log_record.worker_id == "w456"

    def test_should_handle_case_insensitive_faststream_worker_value(
        self, log_record: logging.LogRecord
    ):
        """Test that FASTSTREAM_WORKER value is case-insensitive"""
        # Arrange
        worker_filter = WorkerIdFilter()

        test_cases = ["TRUE", "True", "TrUe", "true"]

        for value in test_cases:
            with patch.dict(os.environ, {"FASTSTREAM_WORKER": value, "WORKER_ID": "w999"}):
                # Act
                result = worker_filter.filter(log_record)

                # Assert
                assert result is True
                assert log_record.worker_id == "w999", f"Failed for value: {value}"

    def test_should_treat_non_true_values_as_false(self, log_record: logging.LogRecord):
        """Test that non-'true' values are treated as false"""
        # Arrange
        worker_filter = WorkerIdFilter()

        test_cases = ["false", "FALSE", "0", "no", "anything", ""]

        for value in test_cases:
            with patch.dict(os.environ, {"FASTSTREAM_WORKER": value}, clear=True):
                # Act
                result = worker_filter.filter(log_record)

                # Assert
                assert result is True
                assert log_record.worker_id == "", f"Failed for value: {value}"

    def test_should_always_return_true(self, log_record: logging.LogRecord):
        """Test that filter always returns True (never filters out records)"""
        # Arrange
        worker_filter = WorkerIdFilter()

        # Act - Test with worker enabled
        with patch.dict(os.environ, {"FASTSTREAM_WORKER": "true"}):
            result1 = worker_filter.filter(log_record)

        # Act - Test with worker disabled
        with patch.dict(os.environ, {"FASTSTREAM_WORKER": "false"}):
            result2 = worker_filter.filter(log_record)

        # Assert
        assert result1 is True
        assert result2 is True


class TestWorkerIdFormatter:
    """Test the WorkerIdFormatter for conditional worker ID display"""

    @pytest.fixture
    def log_record_with_worker_id(self) -> logging.LogRecord:
        """Create a log record with worker_id attribute"""
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        record.worker_id = "w014"
        return record

    @pytest.fixture
    def log_record_without_worker_id(self) -> logging.LogRecord:
        """Create a log record without worker_id attribute"""
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        record.worker_id = ""
        return record

    def test_should_add_worker_prefix_when_worker_id_exists(
        self, log_record_with_worker_id: logging.LogRecord
    ):
        """Test that [w014] prefix is added when worker_id exists"""
        # Arrange
        formatter = WorkerIdFormatter("%(worker_prefix)s - %(message)s")

        # Act
        result = formatter.format(log_record_with_worker_id)

        # Assert
        assert hasattr(log_record_with_worker_id, "worker_prefix")
        assert log_record_with_worker_id.worker_prefix == " - [w014]"
        assert " - [w014] - Test message" in result

    def test_should_add_empty_prefix_when_worker_id_is_empty(
        self, log_record_without_worker_id: logging.LogRecord
    ):
        """Test that empty prefix is added when worker_id is empty"""
        # Arrange
        formatter = WorkerIdFormatter("%(worker_prefix)s - %(message)s")

        # Act
        result = formatter.format(log_record_without_worker_id)

        # Assert
        assert hasattr(log_record_without_worker_id, "worker_prefix")
        assert log_record_without_worker_id.worker_prefix == ""
        # Should not have double " - " when prefix is empty
        assert result == " - Test message" or result.startswith(" - ")

    def test_should_handle_missing_worker_id_attribute(self):
        """Test that formatter handles missing worker_id attribute gracefully"""
        # Arrange
        formatter = WorkerIdFormatter("%(worker_prefix)s - %(message)s")
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        # Don't set worker_id attribute

        # Act
        result = formatter.format(record)

        # Assert
        assert hasattr(record, "worker_prefix")
        assert record.worker_prefix == ""
        assert "Test message" in result

    def test_should_format_complete_log_message_with_worker_id(
        self, log_record_with_worker_id: logging.LogRecord
    ):
        """Test complete log message formatting with worker ID"""
        # Arrange
        formatter = WorkerIdFormatter(
            "%(asctime)s%(worker_prefix)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        # Act
        result = formatter.format(log_record_with_worker_id)

        # Assert
        assert "[w014]" in result
        assert "test.logger" in result
        assert "INFO" in result
        assert "Test message" in result

    def test_should_format_complete_log_message_without_worker_id(
        self, log_record_without_worker_id: logging.LogRecord
    ):
        """Test complete log message formatting without worker ID"""
        # Arrange
        formatter = WorkerIdFormatter(
            "%(asctime)s%(worker_prefix)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        # Act
        result = formatter.format(log_record_without_worker_id)

        # Assert
        assert "[w" not in result  # No worker ID brackets
        assert "test.logger" in result
        assert "INFO" in result
        assert "Test message" in result

    def test_should_preserve_worker_prefix_format(
        self, log_record_with_worker_id: logging.LogRecord
    ):
        """Test that worker_prefix format matches expected pattern"""
        # Arrange
        formatter = WorkerIdFormatter("%(worker_prefix)s")

        # Act
        formatter.format(log_record_with_worker_id)

        # Assert
        # Format should be: " - [worker_id]"
        assert log_record_with_worker_id.worker_prefix == " - [w014]"
        assert log_record_with_worker_id.worker_prefix.startswith(" - [")
        assert log_record_with_worker_id.worker_prefix.endswith("]")

    def test_should_work_with_different_worker_ids(self):
        """Test formatter works correctly with various worker ID formats"""
        # Arrange
        formatter = WorkerIdFormatter("%(worker_prefix)s - %(message)s")

        worker_ids = ["w001", "w015", "w999", "w042"]

        for worker_id in worker_ids:
            record = logging.LogRecord(
                name="test.logger",
                level=logging.INFO,
                pathname="test.py",
                lineno=10,
                msg="Test message",
                args=(),
                exc_info=None,
            )
            record.worker_id = worker_id

            # Act
            result = formatter.format(record)

            # Assert
            assert f"[{worker_id}]" in result, f"Failed for worker_id: {worker_id}"
            assert record.worker_prefix == f" - [{worker_id}]"

    def test_should_not_modify_original_log_record_message(
        self, log_record_with_worker_id: logging.LogRecord
    ):
        """Test that formatting doesn't modify the original message"""
        # Arrange
        formatter = WorkerIdFormatter("%(worker_prefix)s - %(message)s")
        original_message = log_record_with_worker_id.msg

        # Act
        formatter.format(log_record_with_worker_id)

        # Assert
        assert log_record_with_worker_id.msg == original_message
