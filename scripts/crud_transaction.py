#!/usr/bin/env python3
"""Transaction-like rollback mechanism for CRUD generation

This module provides a transaction system for the CRUD generator that ensures
atomic operations with automatic rollback in case of failures. It tracks all
file operations, database migrations, and system modifications to provide
complete rollback capability.
"""

import logging
import shutil
import subprocess
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, List, NamedTuple, Optional

# Import from generate_crud to get FieldDefinition and related functions
from generate_crud import FieldDefinition, get_table_name, get_sqlalchemy_column_type


logger = logging.getLogger(__name__)


class CRUDGenerationError(Exception):
    """CRUD generation specific error"""
    pass


class RollbackOperation(NamedTuple):
    """Represents a rollback operation"""
    name: str
    func: Callable
    args: Any


class CRUDTransaction:
    """Transaction manager for CRUD generation with comprehensive rollback support

    This class provides atomic CRUD generation operations with automatic rollback
    in case of any failure. It tracks all file operations, database migrations,
    and system modifications to ensure complete cleanup on errors.

    Usage:
        try:
            with CRUDTransaction(entity_name, fields) as transaction:
                transaction.create_file(path, content)
                transaction.modify_file(path, modifier_func)
                transaction.run_database_migration()
                transaction.commit()
        except Exception as e:
            # Rollback happens automatically
            print(f"Generation failed: {e}")
    """

    def __init__(self, entity_name: str, fields: List[FieldDefinition]):
        self.entity_name = entity_name
        self.fields = fields
        self.project_root = Path(__file__).parent.parent

        # Create unique backup directory
        backup_id = uuid.uuid4().hex[:8]
        self.backup_dir = Path(f"/tmp/crud_backup_{entity_name}_{backup_id}")

        # Rollback tracking
        self.rollback_stack: List[RollbackOperation] = []
        self.committed = False

        # Migration tracking
        self.initial_migration_head: Optional[str] = None
        self.generated_migration_file: Optional[Path] = None

        # Directory tracking for cleanup
        self.created_directories: List[Path] = []

        logger.info(f"Initialized CRUD transaction for {entity_name}")

    def __enter__(self) -> "CRUDTransaction":
        """Enter transaction context"""
        try:
            self.backup_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Started CRUD transaction for {self.entity_name}")

            # Record initial migration state
            try:
                self.initial_migration_head = self._get_current_migration_head()
                logger.debug(f"Initial migration head: {self.initial_migration_head}")
            except Exception as e:
                logger.warning(f"Could not get initial migration head: {e}")
                self.initial_migration_head = None

            return self

        except Exception as e:
            raise CRUDGenerationError(f"Failed to initialize transaction: {e}") from e

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit transaction context with cleanup"""
        if exc_type is not None:
            logger.error(f"Transaction failed with {exc_type.__name__}: {exc_val}")
            self.rollback()
        elif not self.committed:
            logger.warning("Transaction not committed, rolling back")
            self.rollback()
        else:
            self._cleanup_backup()
            logger.info(f"CRUD transaction completed successfully for {self.entity_name}")

        return False  # Don't suppress exceptions

    def create_file(self, file_path: Path, content: str) -> None:
        """Create or overwrite a file with rollback support

        Args:
            file_path: Path where to create the file
            content: Content to write to the file

        Raises:
            CRUDGenerationError: If file creation fails
        """
        try:
            absolute_path = file_path if file_path.is_absolute() else self.project_root / file_path

            if absolute_path.exists():
                # File exists, back it up for restoration
                backup_path = self._create_backup_path(absolute_path)
                shutil.copy2(str(absolute_path), str(backup_path))
                self.rollback_stack.append(
                    RollbackOperation('restore_file', self._restore_file, (absolute_path, backup_path))
                )
                logger.debug(f"Backed up existing file: {absolute_path}")
            else:
                # New file, mark for deletion on rollback
                self.rollback_stack.append(
                    RollbackOperation('delete_file', self._delete_file, absolute_path)
                )

                # Track parent directories that might need cleanup for new files
                self._track_parent_directories_for_file(absolute_path)

            # Create the file
            absolute_path.parent.mkdir(parents=True, exist_ok=True)
            absolute_path.write_text(content, encoding='utf-8')
            logger.debug(f"Created file: {absolute_path}")

        except Exception as e:
            raise CRUDGenerationError(f"Failed to create file {file_path}: {e}") from e

    def modify_file_content(self, file_path: Path, modifier: Callable[[str], str]) -> None:
        """Modify file content with rollback support

        Args:
            file_path: Path to the file to modify
            modifier: Function that takes current content and returns new content

        Raises:
            CRUDGenerationError: If file modification fails
        """
        try:
            absolute_path = file_path if file_path.is_absolute() else self.project_root / file_path

            if not absolute_path.exists():
                raise CRUDGenerationError(f"Cannot modify non-existent file: {absolute_path}")

            # Backup original content
            original_content = absolute_path.read_text(encoding='utf-8')
            backup_path = self._create_backup_path(absolute_path)
            backup_path.write_text(original_content, encoding='utf-8')
            self.rollback_stack.append(
                RollbackOperation('restore_file', self._restore_file, (absolute_path, backup_path))
            )

            # Apply modification
            new_content = modifier(original_content)
            absolute_path.write_text(new_content, encoding='utf-8')
            logger.debug(f"Modified file: {absolute_path}")

        except Exception as e:
            raise CRUDGenerationError(f"Failed to modify file {file_path}: {e}") from e

    def create_directory(self, dir_path: Path) -> None:
        """Create directory with rollback support

        Args:
            dir_path: Directory path to create
        """
        try:
            absolute_path = dir_path if dir_path.is_absolute() else self.project_root / dir_path

            # Track directories that don't exist before we create them
            directories_to_create = []
            current = absolute_path
            while current != self.project_root and current.parent != current:
                if not current.exists():
                    directories_to_create.append(current)
                else:
                    break  # Stop when we find an existing parent
                current = current.parent

            # Create the directory
            absolute_path.mkdir(parents=True, exist_ok=True)

            # Track created directories for cleanup (in reverse order)
            for directory in reversed(directories_to_create):
                if directory not in self.created_directories:
                    self.created_directories.append(directory)
                    self.rollback_stack.append(
                        RollbackOperation('delete_directory', self._delete_directory, directory)
                    )

            logger.debug(f"Created directory: {absolute_path}")

        except Exception as e:
            raise CRUDGenerationError(f"Failed to create directory {dir_path}: {e}") from e

    def run_database_migration(self) -> None:
        """Run database migration with rollback support

        Generates an Alembic migration file and applies it. In case of rollback,
        both the migration file is removed and the database is reverted to the
        previous state.

        Raises:
            CRUDGenerationError: If migration generation or execution fails
        """
        try:
            # Generate migration file
            migration_file = self._generate_migration_file()
            self.generated_migration_file = migration_file

            # Track migration file for cleanup on rollback
            self.rollback_stack.append(
                RollbackOperation('delete_migration', self._delete_file, migration_file)
            )

            # Execute migration
            self._execute_alembic_upgrade()

            # Track migration rollback if we have an initial head
            if self.initial_migration_head:
                self.rollback_stack.append(
                    RollbackOperation('rollback_migration', self._rollback_migration, self.initial_migration_head)
                )

            logger.info(f"Applied database migration: {migration_file.name}")

        except Exception as e:
            raise CRUDGenerationError(f"Database migration failed: {e}") from e

    def commit(self) -> None:
        """Commit the transaction (mark as successful)

        Once committed, the transaction will not be rolled back even if
        an exception occurs after this point.
        """
        self.committed = True
        logger.info(f"CRUD transaction committed for {self.entity_name}")

    def rollback(self) -> None:
        """Execute rollback operations in reverse order

        This method is called automatically if an exception occurs or if
        the transaction is not committed before exiting the context.
        It attempts to undo all operations in reverse order.
        """
        logger.warning(f"Rolling back CRUD transaction for {self.entity_name}")

        rollback_errors = []
        operations_count = len(self.rollback_stack)

        # Execute rollback operations in reverse order
        for i, operation in enumerate(reversed(self.rollback_stack)):
            try:
                logger.debug(f"Executing rollback {i+1}/{operations_count}: {operation.name}")

                if isinstance(operation.args, tuple):
                    operation.func(*operation.args)
                else:
                    operation.func(operation.args)

                logger.debug(f"✓ Rolled back: {operation.name}")

            except Exception as e:
                error_msg = f"Failed to rollback {operation.name}: {e}"
                logger.error(error_msg)
                rollback_errors.append(error_msg)

        # Clean up empty directories
        self._cleanup_empty_directories()

        # Cleanup backup directory
        self._cleanup_backup()

        if rollback_errors:
            logger.error(f"Rollback completed with {len(rollback_errors)} errors:")
            for error in rollback_errors:
                logger.error(f"  - {error}")
        else:
            logger.info("✅ Rollback completed successfully")

    # Private helper methods

    def _create_backup_path(self, original_path: Path) -> Path:
        """Create a unique backup path for a file"""
        backup_name = f"backup_{len(self.rollback_stack)}_{original_path.name}"
        return self.backup_dir / backup_name

    def _track_parent_directories_for_file(self, file_path: Path) -> None:
        """Track parent directories that may need cleanup when a file is deleted"""
        # Track directories that don't exist before creating file's parent dirs
        directories_to_create = []
        current = file_path.parent
        while current != self.project_root and current.parent != current:
            if not current.exists() and current not in self.created_directories:
                directories_to_create.append(current)
                self.created_directories.append(current)
            else:
                break  # Stop when we find an existing parent
            current = current.parent

        # Add rollback operations for the directories (in reverse order)
        for directory in reversed(directories_to_create):
            self.rollback_stack.append(
                RollbackOperation('delete_directory', self._delete_directory, directory)
            )

    def _track_created_directories(self, directory: Path) -> None:
        """Track created directories for cleanup on rollback (legacy method)"""
        current = directory
        while current != self.project_root and current.parent != current:
            if current not in self.created_directories:
                self.created_directories.append(current)
            current = current.parent

    def _restore_file(self, file_path: Path, backup_path: Path) -> None:
        """Restore a file from backup"""
        if backup_path.exists():
            shutil.copy2(str(backup_path), str(file_path))
            logger.debug(f"Restored file: {file_path}")
        else:
            logger.warning(f"Backup file not found: {backup_path}")

    def _delete_file(self, file_path: Path) -> None:
        """Delete a file if it exists"""
        if file_path.exists():
            file_path.unlink()
            logger.debug(f"Deleted file: {file_path}")

    def _delete_directory(self, dir_path: Path) -> None:
        """Delete a directory if it exists and is empty"""
        try:
            if dir_path.exists():
                # Try to remove directory tree if it contains only directories we created
                contents = list(dir_path.iterdir())
                if not contents:
                    # Directory is empty, safe to remove
                    dir_path.rmdir()
                    logger.debug(f"Deleted empty directory: {dir_path}")
                else:
                    # Check if all contents are directories we created
                    all_created_by_us = all(
                        path.is_dir() and path in self.created_directories
                        for path in contents
                    )
                    if all_created_by_us:
                        # All subdirectories were created by us, remove the whole tree
                        shutil.rmtree(dir_path, ignore_errors=False)
                        logger.debug(f"Deleted directory tree: {dir_path}")
                    else:
                        logger.debug(f"Directory contains files not created by transaction, skipping: {dir_path}")
        except OSError as e:
            logger.debug(f"Could not delete directory {dir_path}: {e}")

    def _cleanup_empty_directories(self) -> None:
        """Clean up empty directories that were created"""
        for directory in reversed(self.created_directories):
            try:
                if directory.exists() and not any(directory.iterdir()):
                    directory.rmdir()
                    logger.debug(f"Removed empty directory: {directory}")
            except OSError as e:
                logger.debug(f"Could not remove directory {directory}: {e}")

    def _cleanup_backup(self) -> None:
        """Clean up backup directory"""
        if self.backup_dir.exists():
            shutil.rmtree(self.backup_dir, ignore_errors=True)
            logger.debug(f"Cleaned up backup directory: {self.backup_dir}")

    def _get_current_migration_head(self) -> Optional[str]:
        """Get current Alembic migration head with fallback strategies"""
        # Strategy 1: Try alembic current
        try:
            result = subprocess.run(
                ["poetry", "run", "alembic", "current"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=True,
                timeout=30
            )

            # Extract revision ID from output like "86134d8125b5 (head)"
            if result.stdout.strip():
                first_line = result.stdout.strip().split('\n')[0]
                return first_line.split()[0]

        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, IndexError) as e:
            logger.warning(f"Could not get current migration head via 'alembic current': {e}")

        # Strategy 2: Try alembic heads as fallback
        try:
            result = subprocess.run(
                ["poetry", "run", "alembic", "heads"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=True,
                timeout=30
            )

            # Extract revision ID from output like "86134d8125b5 (head)"
            if result.stdout.strip():
                first_line = result.stdout.strip().split('\n')[0]
                head_revision = first_line.split()[0]
                logger.info(f"Using heads as fallback, found: {head_revision}")
                return head_revision

        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, IndexError) as e:
            logger.warning(f"Could not get migration head via 'alembic heads': {e}")

        # Strategy 3: Try to fix orphaned version in database
        try:
            self._fix_orphaned_migration_version()
            # Retry alembic current after fix
            result = subprocess.run(
                ["poetry", "run", "alembic", "current"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=True,
                timeout=30
            )
            if result.stdout.strip():
                first_line = result.stdout.strip().split('\n')[0]
                fixed_revision = first_line.split()[0]
                logger.info(f"Fixed orphaned migration, current head: {fixed_revision}")
                return fixed_revision
        except Exception as e:
            logger.warning(f"Could not fix orphaned migration: {e}")

        # Strategy 4: Return None if all strategies fail
        logger.warning("Could not determine current migration head, proceeding without migration rollback support")
        return None

    def _fix_orphaned_migration_version(self) -> None:
        """Fix orphaned migration version in database by updating to latest available head"""
        try:
            # Get available heads from files
            result = subprocess.run(
                ["poetry", "run", "alembic", "heads"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=True,
                timeout=30
            )

            if result.stdout.strip():
                available_head = result.stdout.strip().split('\n')[0].split()[0]
                logger.info(f"Attempting to fix orphaned migration to: {available_head}")

                # Use alembic stamp to fix the version
                subprocess.run(
                    ["poetry", "run", "alembic", "stamp", available_head],
                    cwd=self.project_root,
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=30
                )
                logger.info(f"Successfully stamped migration to: {available_head}")

        except Exception as e:
            logger.warning(f"Failed to fix orphaned migration: {e}")
            raise

    def _generate_migration_file(self) -> Path:
        """Generate Alembic migration file for the entity"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        revision_id = uuid.uuid4().hex[:12]
        table_name = get_table_name(self.entity_name)

        migration_file = f"{timestamp}_add_{self.entity_name}_table.py"
        migrations_dir = self.project_root / "alembic" / "versions"
        migration_path = migrations_dir / migration_file

        # Build column definitions
        column_defs = []
        import_lines = ["import sqlalchemy as sa"]

        for field in self.fields:
            if field.name in ['id', 'created_at', 'updated_at']:
                continue  # Skip base model fields

            col_type = get_sqlalchemy_column_type(field.type_)
            nullable = "True" if field.optional else "False"

            if field.type_ == "uuid" and "import uuid" not in import_lines:
                import_lines.append("import uuid")

            # Build column definition with default value inside the Column() call
            default_part = ""
            if field.default:
                if field.type_ in ["str", "text"]:
                    default_part = f", default='{field.default}'"
                elif field.type_ == "bool":
                    default_part = f", default={field.default}"
                elif field.type_ in ["int", "float"]:
                    default_part = f", default={field.default}"
                elif field.type_ == "uuid" and field.default == "uuid4":
                    default_part = f", default=uuid.uuid4"

            column_def = f"    sa.Column('{field.name}', {col_type}, nullable={nullable}{default_part})"
            column_defs.append(column_def)

        imports_str = "\n".join(import_lines)
        columns_str = ",\n".join(column_defs)

        migration_content = f'''"""{self.entity_name.title()} table

Revision ID: {revision_id}
Revises: {self.initial_migration_head or ''}
Create Date: {datetime.now().isoformat()}

"""
from alembic import op
{imports_str}


# revision identifiers, used by Alembic.
revision = '{revision_id}'
down_revision = {repr(self.initial_migration_head)}
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create {table_name} table"""
    op.create_table('{table_name}',
    sa.Column('id', sa.UUID(), nullable=False),
{columns_str},
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    """Drop {table_name} table"""
    op.drop_table('{table_name}')
'''

        migration_path.write_text(migration_content, encoding='utf-8')
        logger.debug(f"Generated migration file: {migration_file}")
        return migration_path

    def _execute_alembic_upgrade(self) -> None:
        """Execute Alembic upgrade to head with multiple heads handling"""
        try:
            # First attempt: upgrade to head
            result = subprocess.run(
                ["poetry", "run", "alembic", "upgrade", "head"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=True,
                timeout=60
            )

            if result.stdout:
                logger.debug(f"Alembic output: {result.stdout.strip()}")

        except subprocess.CalledProcessError as e:
            # Check if it's a multiple heads error
            error_output = e.stderr if e.stderr else str(e)
            if "Multiple head revisions are present" in error_output:
                logger.warning("Multiple heads detected, attempting to merge...")
                try:
                    # Try to merge heads automatically
                    merge_result = subprocess.run(
                        ["poetry", "run", "alembic", "merge", "heads", "-m", f"merge heads for {self.entity_name}"],
                        cwd=self.project_root,
                        capture_output=True,
                        text=True,
                        check=True,
                        timeout=60
                    )
                    logger.info("Successfully merged heads")

                    # Try upgrade again after merge
                    result = subprocess.run(
                        ["poetry", "run", "alembic", "upgrade", "head"],
                        cwd=self.project_root,
                        capture_output=True,
                        text=True,
                        check=True,
                        timeout=60
                    )
                    logger.info("Successfully upgraded after merge")
                    return

                except subprocess.CalledProcessError as merge_error:
                    logger.error(f"Failed to merge heads: {merge_error}")

            # If not multiple heads error or merge failed, re-raise original error
            error_msg = f"Alembic upgrade failed: {error_output}"
            logger.error(error_msg)
            raise CRUDGenerationError(error_msg) from e

        except subprocess.TimeoutExpired as e:
            error_msg = "Alembic upgrade timed out after 60 seconds"
            logger.error(error_msg)
            raise CRUDGenerationError(error_msg) from e

    def _rollback_migration(self, target_head: str) -> None:
        """Rollback migration to target head"""
        try:
            if target_head:
                result = subprocess.run(
                    ["poetry", "run", "alembic", "downgrade", target_head],
                    cwd=self.project_root,
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=60
                )
                logger.debug(f"Migration rolled back to: {target_head}")
            else:
                # If no previous head, downgrade to base
                result = subprocess.run(
                    ["poetry", "run", "alembic", "downgrade", "base"],
                    cwd=self.project_root,
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=60
                )
                logger.debug("Migration rolled back to base")

        except subprocess.CalledProcessError as e:
            logger.error(f"Migration rollback failed: {e.stderr if e.stderr else str(e)}")
            # Don't raise here as we're already in rollback mode
        except subprocess.TimeoutExpired as e:
            logger.error("Migration rollback timed out")


def create_transaction_context(entity_name: str, fields: List[FieldDefinition]) -> CRUDTransaction:
    """Create a new CRUD transaction context

    Args:
        entity_name: Name of the entity to generate CRUD for
        fields: List of field definitions for the entity

    Returns:
        CRUDTransaction: Transaction context manager
    """
    return CRUDTransaction(entity_name, fields)
