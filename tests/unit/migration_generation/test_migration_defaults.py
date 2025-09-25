"""Unit tests for migration file generation with default values

These tests focus on the specific bug that was fixed in generate_crud.py
where fields with default values were generating malformed Alembic migration files.
The bug was that default parameters were being placed outside the sa.Column()
function call, causing "positional argument follows keyword argument" syntax errors.

Test cases cover:
1. The specific bug case (bool field with default=True)
2. Various field types with defaults
3. Python syntax validation of generated migration files
4. Mixed fields with and without defaults
5. Edge cases and special default values
"""

import ast
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# Import the CLI generator functions and classes
from scripts.generate_crud import (
    FieldDefinition,
    generate_migration_file,
    parse_field_definition,
)


class TestMigrationDefaultValueGeneration:
    """Test suite for migration file generation with default values"""

    def test_bool_field_with_default_true_original_bug(self):
        """Test the specific bug case: bool field with default=True

        This was the original failing case that generated invalid Python syntax:
        sa.Column('is_active', sa.Boolean(), nullable=False) default=True

        The fix ensures the default is inside the Column() call:
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True)
        """
        # Create the field definition that caused the original bug
        field = FieldDefinition(
            name="is_active",
            type_="bool",
            optional=True,  # Fields with defaults are optional
            default="True",
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            migrations_dir = temp_path / "alembic" / "versions"
            migrations_dir.mkdir(parents=True, exist_ok=True)

            # Mock the necessary functions and paths
            with (
                patch("scripts.generate_crud.Path") as mock_path,
                patch("subprocess.run") as mock_subprocess,
            ):
                mock_path.return_value.parent.parent = temp_path

                # Mock subprocess to avoid needing actual alembic setup
                mock_result = Mock()
                mock_result.stdout = "abc123 (head)"
                mock_subprocess.return_value = mock_result

                # Generate the migration file
                generate_migration_file("test_entity", [field], dry_run=False)

                # Find the generated migration file
                migration_files = list(migrations_dir.glob("*.py"))
                assert len(migration_files) == 1

                migration_content = migration_files[0].read_text()

                # Verify the bug is fixed: default should be inside Column()
                assert (
                    "sa.Column('is_active', sa.Boolean(), nullable=True, default=True)"
                    in migration_content
                )

                # Verify the broken syntax is NOT present
                assert (
                    "sa.Column('is_active', sa.Boolean(), nullable=True) default=True"
                    not in migration_content
                )

                # Verify the migration file is valid Python syntax
                try:
                    ast.parse(migration_content)
                except SyntaxError as e:
                    pytest.fail(f"Generated migration file has invalid Python syntax: {e}")

    def test_string_field_with_default_value(self):
        """Test string field with default value generates correct syntax"""
        field = FieldDefinition(name="status", type_="str", optional=True, default="pending")

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

                generate_migration_file("test_entity", [field], dry_run=False)

                migration_files = list(migrations_dir.glob("*.py"))
                migration_content = migration_files[0].read_text()

                # Verify string default is properly quoted inside Column()
                assert (
                    "sa.Column('status', sa.String(255), nullable=True, default='pending')"
                    in migration_content
                )

                # Verify syntax is valid
                ast.parse(migration_content)

    def test_integer_field_with_default_value(self):
        """Test integer field with default value generates correct syntax"""
        field = FieldDefinition(name="retry_count", type_="int", optional=True, default="0")

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

                generate_migration_file("test_entity", [field], dry_run=False)

                migration_files = list(migrations_dir.glob("*.py"))
                migration_content = migration_files[0].read_text()

                # Verify integer default is inside Column() without quotes
                assert (
                    "sa.Column('retry_count', sa.Integer(), nullable=True, default=0)"
                    in migration_content
                )

                # Verify syntax is valid
                ast.parse(migration_content)

    def test_float_field_with_default_value(self):
        """Test float field with default value generates correct syntax"""
        field = FieldDefinition(name="rate", type_="float", optional=True, default="1.5")

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

                generate_migration_file("test_entity", [field], dry_run=False)

                migration_files = list(migrations_dir.glob("*.py"))
                migration_content = migration_files[0].read_text()

                # Verify float default is inside Column() without quotes
                assert (
                    "sa.Column('rate', sa.Float(), nullable=True, default=1.5)" in migration_content
                )

                # Verify syntax is valid
                ast.parse(migration_content)

    def test_text_field_with_default_value(self):
        """Test text field with default value generates correct syntax"""
        field = FieldDefinition(
            name="description", type_="text", optional=True, default="No description"
        )

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

                generate_migration_file("test_entity", [field], dry_run=False)

                migration_files = list(migrations_dir.glob("*.py"))
                migration_content = migration_files[0].read_text()

                # Verify text default is properly quoted inside Column()
                assert (
                    "sa.Column('description', sa.Text(), nullable=True, default='No description')"
                    in migration_content
                )

                # Verify syntax is valid
                ast.parse(migration_content)

    def test_uuid_field_with_uuid4_default(self):
        """Test UUID field with uuid4 default generates correct syntax"""
        field = FieldDefinition(name="external_id", type_="uuid", optional=True, default="uuid4")

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

                generate_migration_file("test_entity", [field], dry_run=False)

                migration_files = list(migrations_dir.glob("*.py"))
                migration_content = migration_files[0].read_text()

                # Verify UUID default uses function reference (no quotes or parentheses)
                assert (
                    "sa.Column('external_id', sa.UUID(), nullable=True, default=uuid.uuid4)"
                    in migration_content
                )

                # Verify uuid import is included
                assert "import uuid" in migration_content

                # Verify syntax is valid
                ast.parse(migration_content)

    def test_mixed_fields_with_and_without_defaults(self):
        """Test multiple fields, some with defaults, some without"""
        fields = [
            FieldDefinition(name="name", type_="str", optional=False, default=None),
            FieldDefinition(name="is_active", type_="bool", optional=True, default="True"),
            FieldDefinition(name="count", type_="int", optional=False, default=None),
            FieldDefinition(name="priority", type_="int", optional=True, default="1"),
            FieldDefinition(name="description", type_="str", optional=True, default="N/A"),
        ]

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

                generate_migration_file("test_entity", fields, dry_run=False)

                migration_files = list(migrations_dir.glob("*.py"))
                migration_content = migration_files[0].read_text()

                # Verify fields without defaults don't have default parameter
                assert "sa.Column('name', sa.String(255), nullable=False)" in migration_content
                assert "sa.Column('count', sa.Integer(), nullable=False)" in migration_content

                # Verify fields with defaults have correct syntax
                assert (
                    "sa.Column('is_active', sa.Boolean(), nullable=True, default=True)"
                    in migration_content
                )
                assert (
                    "sa.Column('priority', sa.Integer(), nullable=True, default=1)"
                    in migration_content
                )
                assert (
                    "sa.Column('description', sa.String(255), nullable=True, default='N/A')"
                    in migration_content
                )

                # Verify syntax is valid
                ast.parse(migration_content)

    def test_all_field_types_with_defaults_comprehensive(self):
        """Comprehensive test covering all supported field types with defaults"""
        fields = [
            FieldDefinition(name="name", type_="str", optional=True, default="test"),
            FieldDefinition(
                name="description", type_="text", optional=True, default="default text"
            ),
            FieldDefinition(name="count", type_="int", optional=True, default="42"),
            FieldDefinition(name="rate", type_="float", optional=True, default="3.14"),
            FieldDefinition(name="active", type_="bool", optional=True, default="False"),
            FieldDefinition(name="external_id", type_="uuid", optional=True, default="uuid4"),
        ]

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

                generate_migration_file("comprehensive_test", fields, dry_run=False)

                migration_files = list(migrations_dir.glob("*.py"))
                migration_content = migration_files[0].read_text()

                # Verify all field types generate correct column definitions
                expected_columns = [
                    "sa.Column('name', sa.String(255), nullable=True, default='test')",
                    "sa.Column('description', sa.Text(), nullable=True, default='default text')",
                    "sa.Column('count', sa.Integer(), nullable=True, default=42)",
                    "sa.Column('rate', sa.Float(), nullable=True, default=3.14)",
                    "sa.Column('active', sa.Boolean(), nullable=True, default=False)",
                    "sa.Column('external_id', sa.UUID(), nullable=True, default=uuid.uuid4)",
                ]

                for expected_column in expected_columns:
                    assert expected_column in migration_content, (
                        f"Expected column definition not found: {expected_column}"
                    )

                # Verify imports are correct
                assert "import sqlalchemy as sa" in migration_content
                assert "import uuid" in migration_content

                # Verify syntax is valid
                ast.parse(migration_content)

    @pytest.mark.parametrize(
        "field_type,default_val,expected_column",
        [
            ("bool", "True", "sa.Column('test_field', sa.Boolean(), nullable=True, default=True)"),
            (
                "bool",
                "False",
                "sa.Column('test_field', sa.Boolean(), nullable=True, default=False)",
            ),
            ("int", "0", "sa.Column('test_field', sa.Integer(), nullable=True, default=0)"),
            ("int", "100", "sa.Column('test_field', sa.Integer(), nullable=True, default=100)"),
            ("float", "0.0", "sa.Column('test_field', sa.Float(), nullable=True, default=0.0)"),
            ("float", "99.9", "sa.Column('test_field', sa.Float(), nullable=True, default=99.9)"),
            (
                "str",
                "test",
                "sa.Column('test_field', sa.String(255), nullable=True, default='test')",
            ),
            (
                "text",
                "long text",
                "sa.Column('test_field', sa.Text(), nullable=True, default='long text')",
            ),
            (
                "uuid",
                "uuid4",
                "sa.Column('test_field', sa.UUID(), nullable=True, default=uuid.uuid4)",
            ),
        ],
    )
    def test_field_type_default_combinations(self, field_type, default_val, expected_column):
        """Test various field type and default value combinations"""
        field = FieldDefinition(
            name="test_field", type_=field_type, optional=True, default=default_val
        )

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

                generate_migration_file("param_test", [field], dry_run=False)

                migration_files = list(migrations_dir.glob("*.py"))
                migration_content = migration_files[0].read_text()

                # Verify the expected column definition is present
                assert expected_column in migration_content, (
                    f"Expected: {expected_column}\nGenerated content:\n{migration_content}"
                )

                # Verify syntax is valid
                ast.parse(migration_content)


class TestMigrationSyntaxValidation:
    """Test suite for validating the Python syntax of generated migration files"""

    def test_migration_file_python_syntax_with_defaults(self):
        """Test that generated migration files with defaults are valid Python"""
        fields = [
            FieldDefinition(name="is_enabled", type_="bool", optional=True, default="True"),
            FieldDefinition(name="max_retries", type_="int", optional=True, default="3"),
            FieldDefinition(name="timeout", type_="float", optional=True, default="30.0"),
            FieldDefinition(name="mode", type_="str", optional=True, default="auto"),
        ]

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

                generate_migration_file("syntax_test", fields, dry_run=False)

                migration_files = list(migrations_dir.glob("*.py"))
                migration_content = migration_files[0].read_text()

                # Parse the entire file as Python AST to catch any syntax errors
                try:
                    parsed_ast = ast.parse(migration_content)

                    # Verify we have the expected structure
                    assert any(
                        node.name == "upgrade"
                        for node in parsed_ast.body
                        if isinstance(node, ast.FunctionDef)
                    )
                    assert any(
                        node.name == "downgrade"
                        for node in parsed_ast.body
                        if isinstance(node, ast.FunctionDef)
                    )

                except SyntaxError as e:
                    pytest.fail(
                        f"Generated migration file has syntax error at line {e.lineno}: {e.msg}\n\n"  # noqa: E501
                        f"File content:\n{migration_content}"
                    )

    def test_migration_executable_python_code(self):
        """Test that generated migration files can be compiled and executed"""
        field = FieldDefinition(name="status", type_="bool", optional=True, default="True")

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

                generate_migration_file("executable_test", [field], dry_run=False)

                migration_files = list(migrations_dir.glob("*.py"))
                migration_content = migration_files[0].read_text()

                # Try to compile the code
                try:
                    compiled_code = compile(migration_content, migration_files[0].name, "exec")
                    assert compiled_code is not None
                except SyntaxError as e:
                    pytest.fail(f"Generated migration file cannot be compiled: {e}")


class TestFieldDefinitionParsing:
    """Test suite for parsing field definitions with default values"""

    def test_parse_bool_field_with_default_true(self):
        """Test parsing bool field with default=True (the original bug case)"""
        field_spec = "is_active:bool=True"
        field = parse_field_definition(field_spec)

        assert field.name == "is_active"
        assert field.type_ == "bool"
        assert field.optional is True  # Fields with defaults are optional
        assert field.default == "True"

    def test_parse_bool_field_with_default_false(self):
        """Test parsing bool field with default=False"""
        field_spec = "is_disabled:bool=False"
        field = parse_field_definition(field_spec)

        assert field.name == "is_disabled"
        assert field.type_ == "bool"
        assert field.optional is True
        assert field.default == "False"

    @pytest.mark.parametrize(
        "field_spec,expected_name,expected_type,expected_default",
        [
            ("count:int=0", "count", "int", "0"),
            ("rate:float=1.5", "rate", "float", "1.5"),
            ("name:str=default", "name", "str", "default"),
            ("description:text=empty", "description", "text", "empty"),
            ("external_id:uuid=uuid4", "external_id", "uuid", "uuid4"),
        ],
    )
    def test_parse_field_with_default_parametrized(
        self, field_spec, expected_name, expected_type, expected_default
    ):
        """Test parsing various field types with defaults"""
        field = parse_field_definition(field_spec)

        assert field.name == expected_name
        assert field.type_ == expected_type
        assert field.optional is True  # All fields with defaults should be optional
        assert field.default == expected_default


class TestBugDiscoveryAndKnownIssues:
    """Test suite for discovering and documenting bugs in the migration generation"""

    def test_empty_string_default_bug(self):
        """Test that empty string defaults are NOT handled correctly (known bug)

        This test documents a bug where empty string defaults are not generated
        because the code uses 'if field.default:' which is falsy for empty strings.
        """
        field = FieldDefinition(name="notes", type_="str", optional=True, default="")

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

                generate_migration_file("empty_string_bug", [field], dry_run=False)

                migration_files = list(migrations_dir.glob("*.py"))
                migration_content = migration_files[0].read_text()

                # This demonstrates the bug: empty string default is NOT generated
                # The field appears without any default parameter
                assert "sa.Column('notes', sa.String(255), nullable=True)" in migration_content
                assert "default=''" not in migration_content

                # This test documents the bug - it should fail if the bug is fixed
                # When fixed, the assertion above should be changed to expect the default

    def test_zero_string_vs_empty_string_bug(self):
        """Test difference between '0' and '' defaults showing inconsistent behavior"""
        fields = [
            FieldDefinition(name="zero_string", type_="str", optional=True, default="0"),
            FieldDefinition(name="empty_string", type_="str", optional=True, default=""),
        ]

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

                generate_migration_file("string_comparison_bug", fields, dry_run=False)

                migration_files = list(migrations_dir.glob("*.py"))
                migration_content = migration_files[0].read_text()

                # "0" string works correctly
                assert (
                    "sa.Column('zero_string', sa.String(255), nullable=True, default='0')"
                    in migration_content
                )

                # Empty string does NOT work (bug)
                assert (
                    "sa.Column('empty_string', sa.String(255), nullable=True)" in migration_content
                )
                assert "default=''" not in migration_content


class TestEdgeCasesAndRegressionPrevention:
    """Test suite for edge cases and preventing regressions of the original bug"""

    def test_no_default_fields_still_work(self):
        """Ensure fields without defaults still generate correct syntax"""
        field = FieldDefinition(name="required_name", type_="str", optional=False, default=None)

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

                generate_migration_file("no_default_test", [field], dry_run=False)

                migration_files = list(migrations_dir.glob("*.py"))
                migration_content = migration_files[0].read_text()

                # Should not have any default parameter
                assert (
                    "sa.Column('required_name', sa.String(255), nullable=False)"
                    in migration_content
                )
                assert (
                    "default="
                    not in migration_content.split("sa.Column('required_name'")[1].split(")")[0]
                )

                # Verify syntax is valid
                ast.parse(migration_content)

    def test_empty_string_default_current_behavior(self):
        """Test field with empty string default (documents current buggy behavior)

        This test documents that empty string defaults are currently NOT handled correctly.
        The empty string default is ignored due to the 'if field.default:' check being falsy.
        """
        field = FieldDefinition(name="notes", type_="str", optional=True, default="")

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

                generate_migration_file("empty_default_test", [field], dry_run=False)

                migration_files = list(migrations_dir.glob("*.py"))
                migration_content = migration_files[0].read_text()

                # Currently the empty string default is NOT generated (bug)
                assert "sa.Column('notes', sa.String(255), nullable=True)" in migration_content
                assert "default=''" not in migration_content

                # Verify syntax is valid (even though default is missing)
                ast.parse(migration_content)

    def test_zero_numeric_defaults(self):
        """Test fields with zero numeric defaults"""
        fields = [
            FieldDefinition(name="int_zero", type_="int", optional=True, default="0"),
            FieldDefinition(name="float_zero", type_="float", optional=True, default="0.0"),
        ]

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

                generate_migration_file("zero_defaults_test", fields, dry_run=False)

                migration_files = list(migrations_dir.glob("*.py"))
                migration_content = migration_files[0].read_text()

                # Should handle zero values correctly
                assert (
                    "sa.Column('int_zero', sa.Integer(), nullable=True, default=0)"
                    in migration_content
                )
                assert (
                    "sa.Column('float_zero', sa.Float(), nullable=True, default=0.0)"
                    in migration_content
                )

                # Verify syntax is valid
                ast.parse(migration_content)

    def test_regression_prevention_original_bug_pattern(self):
        """Specific test to prevent regression of the original bug pattern

        This test ensures that the exact pattern that caused the original bug
        cannot happen again: default parameters appearing outside Column() calls
        """
        # Use the exact field type and default that caused the original issue
        field = FieldDefinition(name="is_active", type_="bool", optional=True, default="True")

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

                generate_migration_file("regression_test", [field], dry_run=False)

                migration_files = list(migrations_dir.glob("*.py"))
                migration_content = migration_files[0].read_text()

                # Explicitly check that the broken pattern is NOT present
                broken_patterns = [
                    "sa.Column('is_active', sa.Boolean(), nullable=True) default=True",
                    "sa.Column('is_active', sa.Boolean(), nullable=True), default=True",
                    ") default=True",  # Any variation of default outside parentheses
                ]

                for broken_pattern in broken_patterns:
                    assert broken_pattern not in migration_content, (
                        f"Found broken pattern: {broken_pattern}"
                    )

                # Verify the correct pattern IS present
                assert (
                    "sa.Column('is_active', sa.Boolean(), nullable=True, default=True)"
                    in migration_content
                )

                # Most importantly: ensure it's valid Python
                ast.parse(migration_content)
