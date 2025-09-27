#!/usr/bin/env python3
"""
Migration script to update files from direct logging imports to centralized logger.

This script automates the migration from:
    import logging
    logger = logging.getLogger(__name__)

To:
    from core.logger import get_module_logger
    logger = get_module_logger(__name__)

Following CLAUDE.md: boring, simple transformation script.
"""

import argparse
import logging
import re
from pathlib import Path
from typing import List


def setup_script_logging():
    """Setup logging for this script."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )
    return logging.getLogger(__name__)


def find_python_files(directory: Path, exclude_patterns: List[str] = None) -> List[Path]:
    """Find all Python files in the directory tree."""
    if exclude_patterns is None:
        exclude_patterns = ["__pycache__", ".pytest_cache", ".git", "venv", ".venv"]

    python_files = []
    for file_path in directory.rglob("*.py"):
        # Skip files in excluded directories
        if any(pattern in str(file_path) for pattern in exclude_patterns):
            continue
        python_files.append(file_path)

    return python_files


def should_migrate_file(file_path: Path) -> bool:
    """Check if file needs migration."""
    try:
        content = file_path.read_text(encoding="utf-8")

        # Check for import logging
        has_logging_import = re.search(r'^import logging$', content, re.MULTILINE)

        # Check for logger = logging.getLogger(__name__)
        has_getlogger_pattern = re.search(
            r'^logger\s*=\s*logging\.getLogger\(__name__\)$',
            content,
            re.MULTILINE
        )

        return bool(has_logging_import and has_getlogger_pattern)
    except Exception:
        return False


def migrate_file_content(content: str) -> tuple[str, bool]:
    """
    Migrate the content of a file.

    Returns:
        (updated_content, was_modified)
    """
    original_content = content

    # Replace import logging with the new import
    # But only if it's a standalone import, not part of a more complex import
    content = re.sub(
        r'^import logging$',
        'from core.logger import get_module_logger',
        content,
        flags=re.MULTILINE
    )

    # Replace logger = logging.getLogger(__name__)
    content = re.sub(
        r'^logger\s*=\s*logging\.getLogger\(__name__\)$',
        'logger = get_module_logger(__name__)',
        content,
        flags=re.MULTILINE
    )

    was_modified = content != original_content
    return content, was_modified


def migrate_file(file_path: Path, dry_run: bool = False) -> bool:
    """
    Migrate a single file.

    Returns:
        True if file was modified, False otherwise
    """
    try:
        original_content = file_path.read_text(encoding="utf-8")
        new_content, was_modified = migrate_file_content(original_content)

        if was_modified and not dry_run:
            file_path.write_text(new_content, encoding="utf-8")

        return was_modified
    except Exception as e:
        logging.error(f"Failed to migrate {file_path}: {e}")
        return False


def main():
    """Main migration function."""
    parser = argparse.ArgumentParser(description="Migrate logging imports to centralized logger")
    parser.add_argument(
        "directory",
        type=Path,
        nargs="?",
        default=Path("."),
        help="Directory to scan for Python files (default: current directory)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be migrated without making changes"
    )
    parser.add_argument(
        "--exclude",
        nargs="*",
        default=["tests", "scripts", "__pycache__", ".pytest_cache", ".git"],
        help="Patterns to exclude from migration"
    )

    args = parser.parse_args()
    logger = setup_script_logging()

    if not args.directory.exists():
        logger.error(f"Directory does not exist: {args.directory}")
        return 1

    logger.info(f"Scanning for Python files in: {args.directory}")
    if args.dry_run:
        logger.info("DRY RUN MODE - No files will be modified")

    # Find all Python files
    python_files = find_python_files(args.directory, args.exclude)
    logger.info(f"Found {len(python_files)} Python files")

    # Find files that need migration
    files_to_migrate = []
    for file_path in python_files:
        if should_migrate_file(file_path):
            files_to_migrate.append(file_path)

    logger.info(f"Found {len(files_to_migrate)} files that need migration")

    if not files_to_migrate:
        logger.info("No files need migration")
        return 0

    # Show files that will be migrated
    logger.info("Files to migrate:")
    for file_path in files_to_migrate:
        logger.info(f"  - {file_path}")

    if args.dry_run:
        logger.info("DRY RUN COMPLETE - No files were modified")
        return 0

    # Perform migration
    migrated_count = 0
    for file_path in files_to_migrate:
        if migrate_file(file_path, dry_run=args.dry_run):
            migrated_count += 1
            logger.info(f"Migrated: {file_path}")
        else:
            logger.warning(f"Failed to migrate: {file_path}")

    logger.info(f"Migration complete: {migrated_count}/{len(files_to_migrate)} files migrated")
    return 0


if __name__ == "__main__":
    exit(main())
