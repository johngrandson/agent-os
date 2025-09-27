#!/usr/bin/env python3
"""Test suite for CRUD transaction rollback mechanism

This test suite ensures the rollback system works correctly and cleans up
all changes when failures occur during CRUD generation.
"""

import shutil
import sys
from pathlib import Path
from tempfile import mkdtemp

import pytest


# Add the scripts directory to Python path for imports (noqa: E402)
scripts_dir = Path(__file__).parent.parent.parent.parent / "scripts"
sys.path.insert(0, str(scripts_dir))

from crud_transaction import CRUDGenerationError, CRUDTransaction  # noqa: E402
from generate_crud import parse_fields  # noqa: E402


class TestCRUDTransactionRollback:
    """Test class for CRUD transaction rollback functionality."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        temp_dir = Path(mkdtemp())
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_file_creation_rollback_should_cleanup_on_failure(self, temp_dir):
        """Should roll back file creation when transaction fails."""
        # Arrange
        entity_name = "test_entity"
        fields = parse_fields("name:str,active:bool=True")
        test_file = temp_dir / f"test_rollback_{entity_name}.txt"

        # Act & Assert
        with pytest.raises(Exception, match="Intentional test error"):
            with CRUDTransaction(entity_name, fields) as transaction:
                # Create a test file
                transaction.create_file(test_file, "test content")

                # Verify file was created
                assert test_file.exists(), "File should be created"

                # Force an error to trigger rollback
                raise Exception("Intentional test error")

        # Assert - Verify file was cleaned up
        assert not test_file.exists(), f"File {test_file} should be cleaned up after rollback"

    def test_file_modification_rollback_should_restore_original_content(self, temp_dir):
        """Should restore original file content when transaction fails."""
        # Arrange
        entity_name = "test_modify"
        fields = parse_fields("name:str")
        test_file = temp_dir / f"test_modify_{entity_name}.txt"
        original_content = "original content"
        modified_content = "modified content"

        # Create file with original content
        test_file.write_text(original_content)

        # Act & Assert
        with pytest.raises(Exception, match="Intentional modification test error"):
            with CRUDTransaction(entity_name, fields) as transaction:
                # Modify the file
                transaction.modify_file_content(test_file, lambda _: modified_content)

                # Verify file was modified
                assert test_file.read_text() == modified_content, "File should be modified"

                # Force an error to trigger rollback
                raise Exception("Intentional modification test error")

        # Assert - Verify file was restored to original content
        assert test_file.exists(), "File should still exist"
        assert test_file.read_text() == original_content, (
            "File should be restored to original content"
        )

    def test_directory_creation_rollback_should_cleanup_directories(self, temp_dir):
        """Should roll back directory creation when transaction fails."""
        # Arrange
        entity_name = "test_dirs"
        fields = parse_fields("name:str")
        test_dir = temp_dir / f"test_rollback_dir_{entity_name}"
        test_subdir = test_dir / "subdir"
        test_file = test_subdir / "test.txt"

        # Act & Assert
        with pytest.raises(Exception, match="Intentional directory test error"):
            with CRUDTransaction(entity_name, fields) as transaction:
                # Create directory structure
                transaction.create_directory(test_dir)
                transaction.create_directory(test_subdir)
                transaction.create_file(test_file, "test content")

                # Verify structure was created
                assert test_dir.exists(), "Directory should be created"
                assert test_subdir.exists(), "Subdirectory should be created"
                assert test_file.exists(), "File should be created"

                # Force an error to trigger rollback
                raise Exception("Intentional directory test error")

        # Assert - Verify everything was cleaned up
        assert not test_dir.exists(), f"Directory {test_dir} should be cleaned up after rollback"

    def test_successful_transaction_should_preserve_changes(self, temp_dir):
        """Should preserve all changes when transaction succeeds."""
        # Arrange
        entity_name = "test_success"
        fields = parse_fields("name:str,count:int=0")
        test_file = temp_dir / f"success_{entity_name}.txt"
        test_dir = temp_dir / f"success_dir_{entity_name}"

        # Act
        with CRUDTransaction(entity_name, fields) as transaction:
            # Create both file and directory
            transaction.create_file(test_file, "successful content")
            transaction.create_directory(test_dir)
            # Explicitly commit the transaction
            transaction.commit()

        # Assert - Verify everything was preserved
        assert test_file.exists(), "File should be preserved after successful transaction"
        assert test_dir.exists(), "Directory should be preserved after successful transaction"
        assert test_file.read_text() == "successful content", "File content should be preserved"

    def test_partial_failure_rollback_should_cleanup_all_operations(self, temp_dir):
        """Should roll back all operations when any operation fails."""
        # Arrange
        entity_name = "test_partial"
        fields = parse_fields("name:str")
        test_file1 = temp_dir / f"partial1_{entity_name}.txt"
        test_file2 = temp_dir / f"partial2_{entity_name}.txt"
        test_dir = temp_dir / f"partial_dir_{entity_name}"

        # Act & Assert
        with pytest.raises(Exception, match="Partial failure test"):
            with CRUDTransaction(entity_name, fields) as transaction:
                # Create multiple files and directory successfully
                transaction.create_file(test_file1, "content 1")
                transaction.create_directory(test_dir)
                transaction.create_file(test_file2, "content 2")

                # Verify all were created
                assert test_file1.exists(), "First file should be created"
                assert test_dir.exists(), "Directory should be created"
                assert test_file2.exists(), "Second file should be created"

                # Fail after some operations
                raise Exception("Partial failure test")

        # Assert - Verify everything was cleaned up
        assert not test_file1.exists(), "First file should be cleaned up"
        assert not test_dir.exists(), "Directory should be cleaned up"
        assert not test_file2.exists(), "Second file should be cleaned up"
