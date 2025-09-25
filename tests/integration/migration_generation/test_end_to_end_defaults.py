"""Integration tests for end-to-end migration generation with default values

These tests validate that the CLI generator works correctly from start to finish
when handling fields with default values, ensuring the bug fix is properly
integrated into the complete workflow.
"""

import ast
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# Import the CLI generator main functions
from scripts.generate_crud import generate_migration_file, parse_fields


class TestEndToEndMigrationGeneration:
    """Integration tests for the complete migration generation workflow"""

    def test_end_to_end_bool_default_workflow(self):
        """Test complete workflow for bool field with default (the original bug case)"""
        # Simulate the CLI input that would have caused the original bug
        fields_input = "name:str,is_active:bool=True,description:str?"

        # Parse the fields as the CLI would
        parsed_fields = parse_fields(fields_input)

        # Verify the parsed fields are correct
        assert len(parsed_fields) == 3

        name_field = next(f for f in parsed_fields if f.name == "name")
        assert name_field.type_ == "str"
        assert name_field.optional is False
        assert name_field.default is None

        is_active_field = next(f for f in parsed_fields if f.name == "is_active")
        assert is_active_field.type_ == "bool"
        assert is_active_field.optional is True  # Fields with defaults are optional
        assert is_active_field.default == "True"

        description_field = next(f for f in parsed_fields if f.name == "description")
        assert description_field.type_ == "str"
        assert description_field.optional is True  # Optional field
        assert description_field.default is None

        # Generate migration with these fields
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

                generate_migration_file("test_workflow", parsed_fields, dry_run=False)

                migration_files = list(migrations_dir.glob("*.py"))
                assert len(migration_files) == 1
                migration_content = migration_files[0].read_text()

                # Verify the specific fix: bool default is inside Column() call
                assert (
                    "sa.Column('is_active', sa.Boolean(), nullable=True, default=True)"
                    in migration_content
                )

                # Verify other fields are correct
                assert "sa.Column('name', sa.String(255), nullable=False)" in migration_content
                assert (
                    "sa.Column('description', sa.String(255), nullable=True)" in migration_content
                )

                # Ensure the bug pattern is NOT present
                assert (
                    "sa.Column('is_active', sa.Boolean(), nullable=True) default=True"
                    not in migration_content
                )

                # Verify valid Python syntax
                ast.parse(migration_content)

    def test_end_to_end_mixed_defaults_workflow(self):
        """Test complete workflow with multiple field types and mixed defaults"""
        # Complex field specification with various defaults
        fields_input = (
            "name:str,count:int=0,rate:float=1.5,active:bool=False,"
            "notes:text=TODO,external_id:uuid=uuid4"
        )

        parsed_fields = parse_fields(fields_input)

        # Verify parsing is correct
        assert len(parsed_fields) == 6

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

                generate_migration_file("mixed_defaults", parsed_fields, dry_run=False)

                migration_files = list(migrations_dir.glob("*.py"))
                migration_content = migration_files[0].read_text()

                # Verify all field types generate correct column definitions with defaults
                expected_columns = [
                    "sa.Column('name', sa.String(255), nullable=False)",
                    "sa.Column('count', sa.Integer(), nullable=True, default=0)",
                    "sa.Column('rate', sa.Float(), nullable=True, default=1.5)",
                    "sa.Column('active', sa.Boolean(), nullable=True, default=False)",
                    "sa.Column('notes', sa.Text(), nullable=True, default='TODO')",
                    "sa.Column('external_id', sa.UUID(), nullable=True, default=uuid.uuid4)",
                ]

                for expected_column in expected_columns:
                    assert expected_column in migration_content, (
                        f"Missing column: {expected_column}"
                    )

                # Verify imports are correct
                assert "import sqlalchemy as sa" in migration_content
                assert "import uuid" in migration_content

                # Verify valid Python syntax
                ast.parse(migration_content)

    def test_end_to_end_regression_prevention(self):
        """Integration test specifically for preventing regression of the original bug"""

        # This specific combination caused the original syntax error
        problem_fields = "is_enabled:bool=True,max_count:int=100,description:str=default"

        parsed_fields = parse_fields(problem_fields)

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

                # This should not raise any syntax errors during generation
                try:
                    generate_migration_file("regression_prevention", parsed_fields, dry_run=False)
                except SyntaxError:
                    pytest.fail("Migration generation caused syntax error - regression detected!")

                migration_files = list(migrations_dir.glob("*.py"))
                migration_content = migration_files[0].read_text()

                # Verify all problematic patterns are correctly handled
                assert (
                    "sa.Column('is_enabled', sa.Boolean(), nullable=True, default=True)"
                    in migration_content
                )
                assert (
                    "sa.Column('max_count', sa.Integer(), nullable=True, default=100)"
                    in migration_content
                )
                assert (
                    "sa.Column('description', sa.String(255), nullable=True, default='default')"
                    in migration_content
                )

                # Ensure NO broken patterns exist
                broken_patterns = [
                    ") default=True",
                    ") default=100",
                    ") default='default'",
                    ", default=True",  # At end of line
                    ", default=100",
                    ", default='default'",
                ]

                for broken_pattern in broken_patterns:
                    # Only check if the pattern appears in the wrong context
                    if broken_pattern in migration_content:
                        lines_with_pattern = [
                            line
                            for line in migration_content.split("\n")
                            if broken_pattern in line and not line.strip().startswith("sa.Column(")
                        ]
                        assert not lines_with_pattern, (
                            f"Found broken pattern outside Column(): {broken_pattern}"
                        )

                # Most important: the file must be valid Python
                ast.parse(migration_content)

    @pytest.mark.parametrize(
        "entity_name,field_spec",
        [
            ("user", "name:str,active:bool=True"),
            ("product", "title:str,price:float=0.0,available:bool=True"),
            ("order", "status:str=pending,priority:int=1,urgent:bool=False"),
            (
                "company",
                "name:str,employee_count:int=0,active:bool=True,description:text=No description",
            ),
        ],
    )
    def test_end_to_end_parametrized_entities(self, entity_name, field_spec):
        """Test end-to-end generation for various entity types with defaults"""
        parsed_fields = parse_fields(field_spec)

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

                generate_migration_file(entity_name, parsed_fields, dry_run=False)

                migration_files = list(migrations_dir.glob("*.py"))
                assert len(migration_files) == 1

                migration_content = migration_files[0].read_text()

                # Verify table name is correct
                from scripts.generate_crud import get_table_name

                expected_table_name = get_table_name(entity_name)
                assert f"op.create_table('{expected_table_name}'" in migration_content

                # Verify all fields with defaults have correct syntax
                for field in parsed_fields:
                    if field.default:
                        # The field should appear with default inside Column()
                        column_pattern = f"sa.Column('{field.name}'"
                        assert column_pattern in migration_content

                        # Should not have default outside Column()
                        # Look for the pattern where default appears after closing paren
                        import re

                        broken_pattern = f"sa\\.Column\\('{field.name}'.*?\\)\\s*default="
                        assert not re.search(broken_pattern, migration_content), (
                            f"Found broken default pattern for field {field.name}"
                        )

                # Must be valid Python
                ast.parse(migration_content)


class TestCLIIntegration:
    """Test the CLI integration with default values"""

    def test_dry_run_with_defaults_shows_correct_preview(self):
        """Test that dry run shows correct information for fields with defaults"""
        fields_input = "name:str,active:bool=True,count:int=0"

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            with (
                patch("scripts.generate_crud.Path") as mock_path,
                patch("subprocess.run") as mock_subprocess,
                patch("builtins.print") as mock_print,
            ):
                mock_path.return_value.parent.parent = temp_path
                mock_result = Mock()
                mock_result.stdout = "abc123 (head)"
                mock_subprocess.return_value = mock_result

                # Run dry run
                parsed_fields = parse_fields(fields_input)
                generate_migration_file("test_entity", parsed_fields, dry_run=True)

                # Verify dry run message was printed
                mock_print.assert_called()
                print_calls = [call[0][0] for call in mock_print.call_args_list]
                migration_message = next(
                    (msg for msg in print_calls if "Would create migration" in msg), None
                )
                assert migration_message is not None
                assert "add_test_entity_table.py" in migration_message

    def test_field_parsing_edge_cases_with_defaults(self):
        """Test edge cases in field parsing that involve defaults"""
        test_cases = [
            # Basic cases
            ("name:str=test", 1),
            ("active:bool=True", 1),
            ("count:int=0", 1),
            # Multiple fields
            ("name:str=test,active:bool=True", 2),
            ("name:str,active:bool=True,count:int=0", 3),
            # Mixed optional and defaults
            ("name:str,active:bool=True,description:str?", 3),
            # All major types with defaults
            (
                "str_field:str=test,int_field:int=1,float_field:float=1.5,bool_field:bool=True,text_field:text=long,uuid_field:uuid=uuid4",
                6,
            ),
        ]

        for field_spec, expected_count in test_cases:
            parsed_fields = parse_fields(field_spec)
            assert len(parsed_fields) == expected_count

            # Verify fields with defaults are marked as optional
            for field in parsed_fields:
                if field.default is not None:
                    assert field.optional is True, (
                        f"Field {field.name} with default should be optional"
                    )


class TestErrorHandling:
    """Test error handling in migration generation with defaults"""

    def test_generation_continues_with_some_invalid_defaults(self):
        """Test that generation handles edge cases gracefully"""
        # Test with a UUID field that has invalid default (not uuid4)
        # Use a different field name since 'id' is reserved
        fields_input = "name:str,external_id:uuid=invalid"

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

                # Should not crash, but invalid uuid default will be ignored
                generate_migration_file("error_test", parsed_fields, dry_run=False)

                migration_files = list(migrations_dir.glob("*.py"))
                migration_content = migration_files[0].read_text()

                # Invalid UUID default should not be included
                assert "default=invalid" not in migration_content

                # But the field should still exist without default
                assert "sa.Column('external_id', sa.UUID(), nullable=True)" in migration_content

                # File should still be valid Python
                ast.parse(migration_content)
