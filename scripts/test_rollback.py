#!/usr/bin/env python3
"""Test script for CRUD transaction rollback mechanism

This script tests various failure scenarios to ensure the rollback system
works correctly and cleans up all changes.
"""

import sys
from pathlib import Path

# Add the scripts directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent))

from generate_crud import parse_fields
from crud_transaction import CRUDTransaction, CRUDGenerationError


def test_file_creation_rollback():
    """Test that file creation is rolled back on failure"""
    print("🧪 Testing file creation rollback...")

    entity_name = "test_entity"
    fields = parse_fields("name:str,active:bool=True")

    test_file = Path(f"/tmp/test_rollback_{entity_name}.txt")

    try:
        with CRUDTransaction(entity_name, fields) as transaction:
            # Create a test file
            transaction.create_file(test_file, "test content")

            # Verify file was created
            assert test_file.exists(), "File should be created"

            # Force an error to trigger rollback
            raise Exception("Intentional test error")

    except Exception as e:
        if "Intentional test error" not in str(e):
            raise

    # Verify file was cleaned up
    assert not test_file.exists(), f"File {test_file} should be cleaned up after rollback"
    print("✅ File creation rollback test passed")


def test_file_modification_rollback():
    """Test that file modification is rolled back on failure"""
    print("🧪 Testing file modification rollback...")

    entity_name = "test_modify"
    fields = parse_fields("name:str")

    test_file = Path(f"/tmp/test_modify_{entity_name}.txt")
    original_content = "original content"
    modified_content = "modified content"

    try:
        # Create file with original content
        test_file.write_text(original_content)

        with CRUDTransaction(entity_name, fields) as transaction:
            # Modify the file
            transaction.modify_file_content(
                test_file,
                lambda _: modified_content
            )

            # Verify file was modified
            assert test_file.read_text() == modified_content, "File should be modified"

            # Force an error to trigger rollback
            raise Exception("Intentional modification test error")

    except Exception as e:
        if "Intentional modification test error" not in str(e):
            raise

    # Verify file was restored to original content
    assert test_file.exists(), "File should still exist"
    assert test_file.read_text() == original_content, "File should be restored to original content"

    # Cleanup
    test_file.unlink()
    print("✅ File modification rollback test passed")


def test_directory_creation_rollback():
    """Test that directory creation is rolled back on failure"""
    print("🧪 Testing directory creation rollback...")

    entity_name = "test_dirs"
    fields = parse_fields("name:str")

    test_dir = Path(f"/tmp/test_rollback_dir_{entity_name}")
    test_subdir = test_dir / "subdir"
    test_file = test_subdir / "test.txt"

    try:
        with CRUDTransaction(entity_name, fields) as transaction:
            # Create directory structure
            transaction.create_directory(test_subdir)
            transaction.create_file(test_file, "test content")

            # Verify structure was created
            assert test_dir.exists(), "Parent directory should exist"
            assert test_subdir.exists(), "Subdirectory should exist"
            assert test_file.exists(), "File should exist"

            # Force an error to trigger rollback
            raise Exception("Intentional directory test error")

    except Exception as e:
        if "Intentional directory test error" not in str(e):
            raise

    # Verify directories were cleaned up
    assert not test_dir.exists(), f"Directory {test_dir} should be cleaned up after rollback"
    print("✅ Directory creation rollback test passed")


def test_successful_transaction():
    """Test that successful transactions don't get rolled back"""
    print("🧪 Testing successful transaction (no rollback)...")

    entity_name = "test_success"
    fields = parse_fields("name:str")

    test_file = Path(f"/tmp/test_success_{entity_name}.txt")

    try:
        with CRUDTransaction(entity_name, fields) as transaction:
            # Create a test file
            transaction.create_file(test_file, "success content")

            # Verify file was created
            assert test_file.exists(), "File should be created"

            # Commit the transaction
            transaction.commit()

        # Verify file still exists after successful transaction
        assert test_file.exists(), "File should still exist after successful transaction"
        assert test_file.read_text() == "success content", "File should have correct content"

    finally:
        # Cleanup
        if test_file.exists():
            test_file.unlink()

    print("✅ Successful transaction test passed")


def test_partial_failure_rollback():
    """Test rollback when some operations succeed and others fail"""
    print("🧪 Testing partial failure rollback...")

    entity_name = "test_partial"
    fields = parse_fields("name:str,count:int=0")

    file1 = Path(f"/tmp/test_partial_1_{entity_name}.txt")
    file2 = Path(f"/tmp/test_partial_2_{entity_name}.txt")
    file3 = Path(f"/tmp/test_partial_3_{entity_name}.txt")

    try:
        with CRUDTransaction(entity_name, fields) as transaction:
            # Create first file (should succeed)
            transaction.create_file(file1, "content 1")
            assert file1.exists(), "First file should be created"

            # Create second file (should succeed)
            transaction.create_file(file2, "content 2")
            assert file2.exists(), "Second file should be created"

            # Try to modify non-existent file (should fail)
            transaction.modify_file_content(
                file3,  # This file doesn't exist
                lambda content: content + " modified"
            )

    except CRUDGenerationError as e:
        # This is expected - rollback should happen
        pass

    # Verify all files were cleaned up
    assert not file1.exists(), f"File {file1} should be cleaned up"
    assert not file2.exists(), f"File {file2} should be cleaned up"
    assert not file3.exists(), f"File {file3} should not exist"

    print("✅ Partial failure rollback test passed")


def run_all_tests():
    """Run all rollback tests"""
    print("🚀 Starting CRUD transaction rollback tests...\n")

    tests = [
        test_file_creation_rollback,
        test_file_modification_rollback,
        test_directory_creation_rollback,
        test_successful_transaction,
        test_partial_failure_rollback,
    ]

    passed = 0
    failed = 0

    for test_func in tests:
        try:
            test_func()
            passed += 1
        except Exception as e:
            print(f"❌ Test {test_func.__name__} failed: {e}")
            failed += 1

        print()  # Add spacing between tests

    print(f"🎯 Test Results: {passed} passed, {failed} failed")

    if failed > 0:
        print("❌ Some tests failed")
        return False
    else:
        print("✅ All tests passed!")
        return True


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
