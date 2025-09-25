"""Demonstration tests showing how the original bug would have been caught

This module contains tests that specifically demonstrate:
1. How the original bug manifested
2. How our tests would have caught it before deployment
3. Evidence that the fix works correctly

These tests serve as documentation of the bug fix process.
"""

import ast
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from scripts.generate_crud import generate_migration_file, parse_fields


class TestOriginalBugDemonstration:
    """Tests that demonstrate the original bug and verify the fix"""

    def test_original_bug_would_have_been_caught(self):
        """Demonstrates that our test suite would have caught the original bug

        This test simulates what would have happened with the original buggy code.
        The original bug was that defaults were placed outside the Column() call.
        """

        # The exact field specification that caused the original issue
        fields_input = "name:str,is_active:bool=True,description:str?"
        parsed_fields = parse_fields(fields_input)

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            migrations_dir = temp_path / "alembic" / "versions"
            migrations_dir.mkdir(parents=True, exist_ok=True)

            with (
                patch("scripts.generate_crud.Path") as mock_path,
                patch("subprocess.run") as mock_subprocess,
            ):
                mock_path.return_value.parent.parent = temp_path
                mock_result = Mock()
                mock_result.stdout = "abc123 (head)"
                mock_subprocess.return_value = mock_result

                # Generate the migration
                generate_migration_file("test_entity", parsed_fields, dry_run=False)

                migration_files = list(migrations_dir.glob("*.py"))
                migration_content = migration_files[0].read_text()

                # CRITICAL: The generated migration MUST be valid Python
                # This would have failed with the original bug
                try:
                    ast.parse(migration_content)
                    print("✅ Migration file has valid Python syntax")
                except SyntaxError as e:
                    pytest.fail(f"❌ SYNTAX ERROR (original bug reproduced): {e}")

                # Verify the specific fix is present
                correct_pattern = (
                    "sa.Column('is_active', sa.Boolean(), nullable=True, default=True)"
                )
                assert correct_pattern in migration_content, (
                    f"❌ Correct pattern not found: {correct_pattern}"
                )

                # Verify the broken pattern is NOT present
                broken_pattern = "sa.Column('is_active', sa.Boolean(), nullable=True) default=True"
                assert broken_pattern not in migration_content, (
                    f"❌ Broken pattern still present: {broken_pattern}"
                )

                print(
                    "✅ Bug fix verification: defaults are correctly placed inside Column() calls"
                )

    def test_comprehensive_field_types_all_work_correctly(self):
        """Test that all field types with defaults generate valid syntax"""

        # Comprehensive test covering all the types that could have been affected
        fields_input = (
            "name:str=DefaultName,"
            "count:int=42,"
            "rate:float=3.14,"
            "active:bool=True,"
            "disabled:bool=False,"
            "notes:text=Default notes,"
            "external_id:uuid=uuid4"
        )

        parsed_fields = parse_fields(fields_input)

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            migrations_dir = temp_path / "alembic" / "versions"
            migrations_dir.mkdir(parents=True, exist_ok=True)

            with (
                patch("scripts.generate_crud.Path") as mock_path,
                patch("subprocess.run") as mock_subprocess,
            ):
                mock_path.return_value.parent.parent = temp_path
                mock_result = Mock()
                mock_result.stdout = "abc123 (head)"
                mock_subprocess.return_value = mock_result

                generate_migration_file("comprehensive_test", parsed_fields, dry_run=False)

                migration_files = list(migrations_dir.glob("*.py"))
                migration_content = migration_files[0].read_text()

                # Critical: File must be valid Python
                ast.parse(migration_content)

                # Verify each field type has correct default syntax
                expected_patterns = [
                    "sa.Column('name', sa.String(255), nullable=True, default='DefaultName')",
                    "sa.Column('count', sa.Integer(), nullable=True, default=42)",
                    "sa.Column('rate', sa.Float(), nullable=True, default=3.14)",
                    "sa.Column('active', sa.Boolean(), nullable=True, default=True)",
                    "sa.Column('disabled', sa.Boolean(), nullable=True, default=False)",
                    "sa.Column('notes', sa.Text(), nullable=True, default='Default notes')",
                    "sa.Column('external_id', sa.UUID(), nullable=True, default=uuid.uuid4)",
                ]

                for pattern in expected_patterns:
                    assert pattern in migration_content, f"Missing correct pattern: {pattern}"

                print("✅ All field types with defaults generate correct SQL column definitions")

    def test_migration_files_would_execute_correctly(self):
        """Test that generated migrations would actually run without Python errors"""

        fields_input = "active:bool=True,priority:int=1,name:str=test"
        parsed_fields = parse_fields(fields_input)

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            migrations_dir = temp_path / "alembic" / "versions"
            migrations_dir.mkdir(parents=True, exist_ok=True)

            with (
                patch("scripts.generate_crud.Path") as mock_path,
                patch("subprocess.run") as mock_subprocess,
            ):
                mock_path.return_value.parent.parent = temp_path
                mock_result = Mock()
                mock_result.stdout = "abc123 (head)"
                mock_subprocess.return_value = mock_result

                generate_migration_file("execution_test", parsed_fields, dry_run=False)

                migration_files = list(migrations_dir.glob("*.py"))
                migration_content = migration_files[0].read_text()

                # Test 1: Python syntax is valid
                parsed_ast = ast.parse(migration_content)
                assert parsed_ast is not None

                # Test 2: File can be compiled
                compiled_code = compile(migration_content, migration_files[0].name, "exec")
                assert compiled_code is not None

                # Test 3: The functions are properly defined
                function_names = [
                    node.name for node in parsed_ast.body if isinstance(node, ast.FunctionDef)
                ]
                assert "upgrade" in function_names
                assert "downgrade" in function_names

                print("✅ Migration file would execute without Python syntax errors")

    def test_before_and_after_bug_fix_comparison(self):
        """Demonstrate what the output looks like before and after the fix"""

        fields_input = "is_enabled:bool=True"
        parsed_fields = parse_fields(fields_input)

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            migrations_dir = temp_path / "alembic" / "versions"
            migrations_dir.mkdir(parents=True, exist_ok=True)

            with (
                patch("scripts.generate_crud.Path") as mock_path,
                patch("subprocess.run") as mock_subprocess,
            ):
                mock_path.return_value.parent.parent = temp_path
                mock_result = Mock()
                mock_result.stdout = "abc123 (head)"
                mock_subprocess.return_value = mock_result

                generate_migration_file("comparison_test", parsed_fields, dry_run=False)

                migration_files = list(migrations_dir.glob("*.py"))
                migration_content = migration_files[0].read_text()

                print("\n" + "=" * 60)
                print("BUG FIX DEMONSTRATION")
                print("=" * 60)

                print("\n❌ BEFORE (broken - would cause SyntaxError):")
                print("   sa.Column('is_enabled', sa.Boolean(), nullable=True) default=True")

                print("\n✅ AFTER (fixed - valid Python syntax):")
                print("   sa.Column('is_enabled', sa.Boolean(), nullable=True, default=True)")

                print("\n🔍 ACTUAL GENERATED OUTPUT:")
                for line in migration_content.split("\n"):
                    if "is_enabled" in line and "sa.Column" in line:
                        print(f"   {line.strip()}")
                        break

                print("\n✅ RESULT: Migration file generates valid Python syntax")
                print("=" * 60)

                # Verify it's the correct pattern
                assert (
                    "sa.Column('is_enabled', sa.Boolean(), nullable=True, default=True)"
                    in migration_content
                )
                assert (
                    "sa.Column('is_enabled', sa.Boolean(), nullable=True) default=True"
                    not in migration_content
                )

                # Verify it's valid Python
                ast.parse(migration_content)


if __name__ == "__main__":
    # Run the demonstration if this file is executed directly
    test_instance = TestOriginalBugDemonstration()

    print("🔧 RUNNING BUG FIX DEMONSTRATION TESTS...")
    print("=" * 70)

    test_instance.test_original_bug_would_have_been_caught()
    print("✅ Test 1: Original bug detection - PASSED")

    test_instance.test_comprehensive_field_types_all_work_correctly()
    print("✅ Test 2: All field types work correctly - PASSED")

    test_instance.test_migration_files_would_execute_correctly()
    print("✅ Test 3: Migration files are executable - PASSED")

    test_instance.test_before_and_after_bug_fix_comparison()
    print("✅ Test 4: Before/after comparison - PASSED")

    print("\n🎉 ALL DEMONSTRATION TESTS PASSED!")
    print("   The bug fix is working correctly and our tests would have caught the original issue.")
    print("=" * 70)
