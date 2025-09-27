#!/usr/bin/env python3
"""CLI CRUD generator for FastAPI + SQLAlchemy + Events project

Stage 1: CLI Core + Validation
- Argument parsing with argparse
- Entity name validation (snake_case, no conflicts)
- Field parsing with type validation
- Dry-run mode (show what would be created)
- Force mode (overwrite existing)
- Directory structure creation
"""

import argparse
import re
import sys
from pathlib import Path
from typing import NamedTuple
from datetime import datetime


class FieldDefinition(NamedTuple):
    """Represents a parsed field definition"""
    name: str
    type_: str
    optional: bool
    default: str | None = None


class ValidationError(Exception):
    """Custom exception for validation errors"""
    pass


# Type mappings for template generation
TYPE_MAPPINGS = {
    'str': {
        'sqlalchemy': 'String(255)',
        'python': 'str',
        'pydantic': 'str'
    },
    'int': {
        'sqlalchemy': 'Integer',
        'python': 'int',
        'pydantic': 'int'
    },
    'float': {
        'sqlalchemy': 'Float',
        'python': 'float',
        'pydantic': 'float'
    },
    'bool': {
        'sqlalchemy': 'Boolean',
        'python': 'bool',
        'pydantic': 'bool'
    },
    'text': {
        'sqlalchemy': 'Text',
        'python': 'str',
        'pydantic': 'str'
    },
    'datetime': {
        'sqlalchemy': 'DateTime(timezone=True)',
        'python': 'datetime',
        'pydantic': 'datetime'
    },
    'date': {
        'sqlalchemy': 'Date',
        'python': 'date',
        'pydantic': 'date'
    },
    'time': {
        'sqlalchemy': 'Time',
        'python': 'time',
        'pydantic': 'time'
    },
    'uuid': {
        'sqlalchemy': 'UUID(as_uuid=True)',
        'python': 'UUID',
        'pydantic': 'UUID'
    },
    'json': {
        'sqlalchemy': 'JSON',
        'python': 'dict',
        'pydantic': 'dict'
    },
    'decimal': {
        'sqlalchemy': 'Numeric(precision=10, scale=2)',
        'python': 'Decimal',
        'pydantic': 'Decimal'
    }
}


def to_pascal_case(snake_str: str) -> str:
    """Convert snake_case to PascalCase with safety validation"""
    # Additional safety check - should only contain safe characters
    if not re.match(r'^[a-z][a-z0-9_]*[a-z0-9]$', snake_str):
        raise ValidationError(f"Cannot convert '{snake_str}' to PascalCase - invalid format")
    return ''.join(word.capitalize() for word in snake_str.split('_'))


def to_camel_case(snake_str: str) -> str:
    """Convert snake_case to camelCase with safety validation"""
    # Additional safety check - should only contain safe characters
    if not re.match(r'^[a-z][a-z0-9_]*[a-z0-9]$', snake_str):
        raise ValidationError(f"Cannot convert '{snake_str}' to camelCase - invalid format")
    components = snake_str.split('_')
    return components[0] + ''.join(word.capitalize() for word in components[1:])


def get_table_name(entity_name: str) -> str:
    """Get table name with intelligent pluralization logic

    Args:
        entity_name: The entity name in snake_case

    Returns:
        Pluralized table name using proper English grammar rules
    """
    return get_plural_form(entity_name)


def get_plural_form(word: str) -> str:
    """Convert word to proper plural form using English grammar rules

    Handles compound words (snake_case entities) by pluralizing only the last word.
    Implements standard English pluralization rules for various word endings.

    Args:
        word: The singular form to pluralize

    Returns:
        The correct plural form

    Raises:
        ValueError: If word is empty or contains only underscores
    """
    # Handle edge cases
    if not word:
        raise ValueError("Cannot pluralize empty string")

    if word == "_" or all(c == "_" for c in word):
        raise ValueError("Cannot pluralize string containing only underscores")

    # Handle compound words (snake_case entities)
    if "_" in word:
        parts = word.split("_")
        if not parts[-1]:  # Handle cases like "word_"
            raise ValueError("Invalid compound word ending with underscore")

        # Pluralize only the last word
        last_word_plural = _pluralize_single_word(parts[-1])
        return "_".join(parts[:-1] + [last_word_plural])

    # Handle single words
    return _pluralize_single_word(word)


def _pluralize_single_word(word: str) -> str:
    """Pluralize a single word using English grammar rules

    Args:
        word: Single word to pluralize

    Returns:
        Pluralized form of the word
    """
    if not word:
        return word

    # Words already ending in 's', 'ss', 'x', 'z', 'sh', 'ch' - add 'es'
    # But first check for words that are already plural or don't change
    if word.endswith('s'):
        # Handle special cases that are already plural or don't change
        # Common words that end in 's' but are not plurals
        singular_s_words = {
            'status', 'series', 'news', 'species', 'means',
            'headquarters', 'mathematics', 'physics', 'address',
            'business', 'process', 'access', 'success', 'class'
        }

        # If it's a known singular word ending in 's', pluralize it
        if word in singular_s_words:
            if word in ['status', 'series', 'news', 'species', 'means', 'headquarters']:
                return word  # These don't change in plural
            else:
                return f"{word}es"  # address -> addresses, class -> classes

        # If already plural (ends with common plural patterns), don't change
        if word.endswith(('ies', 'ves', 'ses', 'zes', 'shes', 'ches')):
            return word

        # For other words ending in 's', assume already plural
        return word

    # Words ending in 'y' preceded by a consonant -> change 'y' to 'ies'
    if word.endswith('y') and len(word) > 1:
        if word[-2] not in 'aeiou':  # Consonant before 'y'
            return word[:-1] + 'ies'  # company -> companies
        else:
            return word + 's'  # boy -> boys

    # Words ending in 'f' or 'fe' -> change to 'ves'
    if word.endswith('f'):
        # Some exceptions: chief -> chiefs, roof -> roofs
        f_exceptions = {'chief', 'roof', 'proof', 'cliff', 'staff'}
        if word in f_exceptions:
            return word + 's'
        else:
            return word[:-1] + 'ves'  # leaf -> leaves

    if word.endswith('fe'):
        return word[:-2] + 'ves'  # knife -> knives

    # Words ending in 's', 'ss', 'sh', 'ch', 'x', 'z' -> add 'es'
    if word.endswith(('s', 'ss', 'sh', 'ch', 'x', 'z')):
        return word + 'es'

    # Words ending in 'o' preceded by a consonant -> usually add 'es'
    if word.endswith('o') and len(word) > 1:
        if word[-2] not in 'aeiou':  # Consonant before 'o'
            # Some exceptions: photo -> photos, piano -> pianos
            o_exceptions = {'photo', 'piano', 'halo', 'solo'}
            if word in o_exceptions:
                return word + 's'
            else:
                return word + 'es'  # hero -> heroes
        else:
            return word + 's'  # radio -> radios

    # Regular plurals - just add 's'
    return word + 's'


def get_sqlalchemy_imports(fields: list[FieldDefinition]) -> set[str]:
    """Get required SQLAlchemy imports based on field types"""
    imports = {'String'}  # Always need String for default fields

    for field in fields:
        if field.type_ == 'str':
            imports.add('String')
        elif field.type_ == 'text':
            imports.add('Text')
        elif field.type_ == 'int':
            imports.add('Integer')
        elif field.type_ == 'float':
            imports.add('Float')
        elif field.type_ == 'bool':
            imports.add('Boolean')
        elif field.type_ == 'datetime':
            imports.add('DateTime')
        elif field.type_ == 'date':
            imports.add('Date')
        elif field.type_ == 'time':
            imports.add('Time')
        elif field.type_ == 'uuid':
            # UUID is from sqlalchemy.dialects.postgresql
            pass  # Handled separately in template
        elif field.type_ == 'json':
            imports.add('JSON')
        elif field.type_ == 'decimal':
            imports.add('Numeric')

    return imports


def get_pydantic_imports(fields: list[FieldDefinition]) -> set[str]:
    """Get required imports for Pydantic schemas"""
    imports = set()

    for field in fields:
        if field.type_ == 'datetime':
            imports.add('datetime')
        elif field.type_ == 'date':
            imports.add('date')
        elif field.type_ == 'time':
            imports.add('time')
        elif field.type_ == 'uuid':
            imports.add('UUID')
        elif field.type_ == 'decimal':
            imports.add('Decimal')

    return imports


def validate_entity_name(entity_name: str, allow_existing: bool = False) -> str:
    """Validate entity name is snake_case and doesn't conflict with existing entities

    Args:
        entity_name: The entity name to validate
        allow_existing: If True, don't raise error for existing entities

    Returns:
        The validated entity name

    Raises:
        ValidationError: If entity name is invalid
    """
    if not entity_name:
        raise ValidationError("Entity name cannot be empty")

    # Security check: prevent path traversal attacks
    if '..' in entity_name or '/' in entity_name or '\\' in entity_name:
        raise ValidationError(
            f"Entity name '{entity_name}' contains invalid characters (no path separators or '..' allowed)"
        )

    # Security check: prevent null bytes and other control characters
    if any(ord(c) < 32 for c in entity_name):
        raise ValidationError(
            f"Entity name '{entity_name}' contains invalid control characters"
        )

    # Check snake_case format
    if not re.match(r'^[a-z][a-z0-9_]*[a-z0-9]$', entity_name):
        raise ValidationError(
            f"Entity name '{entity_name}' must be snake_case (lowercase, underscores only)"
        )

    # Check for reserved names
    reserved_names = {'test', 'tests', 'core', 'infrastructure', 'app', 'events', 'api'}
    if entity_name in reserved_names:
        raise ValidationError(f"Entity name '{entity_name}' is reserved")

    # Additional security check: ensure resolved path stays within project
    project_root = Path(__file__).parent.parent
    entity_dir = project_root / "app" / entity_name

    try:
        # Resolve to absolute path and check it's within project
        resolved_path = entity_dir.resolve()
        project_root_resolved = project_root.resolve()

        # Check if the resolved path starts with the project root
        if not str(resolved_path).startswith(str(project_root_resolved)):
            raise ValidationError(
                f"Entity name '{entity_name}' resolves to path outside project directory"
            )
    except (OSError, ValueError) as e:
        raise ValidationError(f"Entity name '{entity_name}' results in invalid path: {e}")

    # Check if entity already exists (unless explicitly allowed)
    if not allow_existing:
        if entity_dir.exists():
            raise ValidationError(f"Entity '{entity_name}' already exists at {entity_dir}")

    return entity_name


def parse_field_definition(field_spec: str) -> FieldDefinition:
    """Parse a single field definition like 'name:str' or 'description:str?'

    Args:
        field_spec: Field specification string

    Returns:
        FieldDefinition with parsed components

    Raises:
        ValidationError: If field specification is invalid
    """
    if ':' not in field_spec:
        raise ValidationError(f"Invalid field spec '{field_spec}': must be 'name:type'")

    name, type_part = field_spec.split(':', 1)
    name = name.strip()
    type_part = type_part.strip()

    # Check for default value first
    default_value = None
    if '=' in type_part:
        type_part, default_value = type_part.split('=', 1)
        default_value = default_value.strip()

        # Security check: prevent injection in default values
        if any(c in default_value for c in ['"', "'", ';', '&', '|', '`', '$', '(', ')']):
            raise ValidationError(
                f"Default value '{default_value}' contains potentially dangerous characters"
            )

        optional = True  # Fields with defaults are optional

    # Check for optional marker
    if type_part.endswith('?'):
        optional = True
        type_part = type_part[:-1]
    elif default_value is not None:
        optional = True
    else:
        optional = False

    # Validate field name (snake_case)
    if not re.match(r'^[a-z][a-z0-9_]*[a-z0-9]$', name):
        raise ValidationError(
            f"Field name '{name}' must be snake_case (lowercase, underscores only)"
        )

    # Validate field type
    valid_types = {'str', 'text', 'int', 'float', 'bool', 'datetime', 'date', 'time', 'uuid', 'json', 'decimal'}
    if type_part not in valid_types:
        raise ValidationError(
            f"Field type '{type_part}' not supported. Valid types: {', '.join(valid_types)}"
        )

    return FieldDefinition(name=name, type_=type_part, optional=optional, default=default_value)


def parse_fields(fields_str: str) -> list[FieldDefinition]:
    """Parse comma-separated field definitions

    Args:
        fields_str: Comma-separated field specifications

    Returns:
        List of parsed FieldDefinition objects

    Raises:
        ValidationError: If any field is invalid
    """
    if not fields_str.strip():
        raise ValidationError("Fields cannot be empty")

    field_specs = [spec.strip() for spec in fields_str.split(',')]
    fields = []
    field_names = set()

    for spec in field_specs:
        if not spec:
            continue

        field = parse_field_definition(spec)

        # Check for duplicate field names
        if field.name in field_names:
            raise ValidationError(f"Duplicate field name '{field.name}'")

        field_names.add(field.name)
        fields.append(field)

    if not fields:
        raise ValidationError("At least one field must be specified")

    return fields


def get_directory_structure(entity_name: str) -> list[Path]:
    """Get list of directories to create for the entity

    Args:
        entity_name: The entity name

    Returns:
        List of Path objects representing directories to create
    """
    project_root = Path(__file__).parent.parent

    directories = [
        project_root / "app" / entity_name,
        project_root / "app" / entity_name / "api",
        project_root / "app" / entity_name / "repositories",
        project_root / "app" / entity_name / "services",
        project_root / "app" / "events" / entity_name,
        project_root / "tests" / "unit" / entity_name,
        project_root / "tests" / "unit" / entity_name / "events",
    ]

    return directories


def create_directories(directories: list[Path], dry_run: bool = False) -> None:
    """Create the directory structure

    Args:
        directories: List of directories to create
        dry_run: If True, only print what would be created
    """
    for directory in directories:
        if dry_run:
            print(f"Would create: {directory}")
        else:
            directory.mkdir(parents=True, exist_ok=True)
            print(f"📁 Created: {directory}")


def generate_model_file(entity_name: str, fields: list[FieldDefinition]) -> str:
    """Generate SQLAlchemy model file content"""
    entity_class = to_pascal_case(entity_name)
    # Get table name using shared logic
    table_name = get_table_name(entity_name)

    sqlalchemy_imports = get_sqlalchemy_imports(fields)
    imports_str = ', '.join(sorted(sqlalchemy_imports))

    # Generate field definitions
    field_definitions = []
    for field in fields:
        sqlalchemy_type = TYPE_MAPPINGS[field.type_]['sqlalchemy']
        python_type = TYPE_MAPPINGS[field.type_]['python']

        if field.optional:
            type_annotation = f"{python_type} | None"
            nullable = "nullable=True"
        else:
            type_annotation = python_type
            nullable = "nullable=False"

        field_def = f'    {field.name}: Mapped[{type_annotation}] = mapped_column({sqlalchemy_type}, {nullable})'
        field_definitions.append(field_def)

    field_definitions_str = '\n'.join(field_definitions)

    # Generate create method parameters
    create_params = []
    create_args = []
    for field in fields:
        python_type = TYPE_MAPPINGS[field.type_]['python']
        if field.optional:
            param = f'{field.name}: {python_type} | None = None'
        else:
            param = f'{field.name}: {python_type}'
        create_params.append(param)
        create_args.append(f'{field.name}={field.name}')

    create_params_str = ',\n        '.join(create_params)
    create_args_str = ',\n            '.join(create_args)

    template = f'''"""SQLAlchemy model for {entity_name}"""

from __future__ import annotations

import uuid

from infrastructure.database import Base
from infrastructure.database.mixins import TimestampMixin
from sqlalchemy import {imports_str}
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column


class {entity_class}(Base, TimestampMixin):
    __tablename__ = "{table_name}"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
{field_definitions_str}

    @classmethod
    def create(
        cls,
        *,
        {create_params_str},
    ) -> {entity_class}:
        return cls(
            {create_args_str},
        )
'''
    return template


def generate_repository_file(entity_name: str, fields: list[FieldDefinition]) -> str:
    """Generate repository file content"""
    entity_class = to_pascal_case(entity_name)
    repository_class = f"{entity_class}Repository"

    # Find a unique field for specialized queries (prefer string fields)
    unique_field = None
    for field in fields:
        if field.type_ == 'str' and not field.optional:
            unique_field = field.name
            break

    unique_method = ""
    if unique_field:
        unique_method = f'''
    async def get_{entity_name}_by_{unique_field}(self, *, {unique_field}: str) -> {entity_class} | None:
        """Find {entity_name} by {unique_field}"""
        async with get_session() as session:
            result = await session.execute(select({entity_class}).where({entity_class}.{unique_field} == {unique_field}))
            return result.scalars().first()'''

    template = f'''"""{entity_class} Repository - direct SQLAlchemy implementation"""

import uuid

from app.{entity_name}.{entity_name} import {entity_class}
from infrastructure.database.session import get_session
from sqlalchemy import select


class {repository_class}:
    """Simplified {entity_name} repository with direct SQLAlchemy implementation"""

    async def get_{entity_name}s(
        self,
        *,
        limit: int = 12,
        prev: int | None = None,
    ) -> list[{entity_class}]:
        """Get paginated list of {entity_name}s"""
        async with get_session() as session:
            query = select({entity_class})

            if prev:
                query = query.where({entity_class}.id < prev)

            if limit > 12:
                limit = 12

            query = query.limit(limit)

            result = await session.execute(query)
            return list(result.scalars().all())

    async def get_{entity_name}_by_id(self, *, {entity_name}_id: uuid.UUID) -> {entity_class} | None:
        """Find {entity_name} by ID"""
        async with get_session() as session:
            result = await session.execute(select({entity_class}).where({entity_class}.id == {entity_name}_id))
            return result.scalars().first()

    async def get_{entity_name}_by_id_with_relations(self, *, {entity_name}_id: uuid.UUID) -> {entity_class} | None:
        """Find {entity_name} by ID with relations eagerly loaded"""
        async with get_session() as session:
            stmt = select({entity_class}).where({entity_class}.id == {entity_name}_id)
            result = await session.execute(stmt)
            return result.scalars().first(){unique_method}

    async def create_{entity_name}(self, *, {entity_name}: {entity_class}) -> {entity_class}:
        """Create a new {entity_name}"""
        async with get_session() as session:
            session.add({entity_name})
            await session.commit()
            await session.refresh({entity_name})
            return {entity_name}

    async def update_{entity_name}(self, *, {entity_name}: {entity_class}) -> {entity_class}:
        """Update existing {entity_name}"""
        async with get_session() as session:
            await session.merge({entity_name})
            await session.commit()
            return {entity_name}

    async def delete_{entity_name}(self, *, {entity_name}: {entity_class}) -> None:
        """Delete {entity_name}"""
        async with get_session() as session:
            await session.delete({entity_name})
            await session.commit()
'''
    return template


def generate_service_file(entity_name: str, fields: list[FieldDefinition]) -> str:
    """Generate service file content"""
    entity_class = to_pascal_case(entity_name)
    service_class = f"{entity_class}Service"
    repository_class = f"{entity_class}Repository"
    publisher_class = f"{entity_class}EventPublisher"

    # Find unique field for business logic validation
    unique_field = None
    for field in fields:
        if field.type_ == 'str' and not field.optional:
            unique_field = field.name
            break

    unique_validation = ""
    unique_check_update = ""
    if unique_field:
        unique_validation = f'''existing_{entity_name} = await self.repository.get_{entity_name}_by_{unique_field}(
            {unique_field}=command.{unique_field}
        )
        if existing_{entity_name}:
            from core.exceptions.domain import {entity_class}AlreadyExists

            raise {entity_class}AlreadyExists'''

        unique_check_update = f'''
        # Check if {unique_field} is being changed and if new {unique_field} already exists
        if {entity_name}.{unique_field} != command.{unique_field}:
            existing_{entity_name} = await self.repository.get_{entity_name}_by_{unique_field}(
                {unique_field}=command.{unique_field}
            )
            if existing_{entity_name} and str(existing_{entity_name}.id) != command.{entity_name}_id:
                from core.exceptions.domain import {entity_class}AlreadyExists

                raise {entity_class}AlreadyExists'''

    # Generate field assignments for create method
    field_data_create = []
    field_data_update = []
    for field in fields:
        field_data_create.append(f'                "{field.name}": {entity_name}.{field.name},')
        field_data_update.append(f'{entity_name}.{field.name} = command.{field.name}')

    field_data_create_str = '\n'.join(field_data_create)
    field_data_update_str = '\n        '.join(field_data_update)

    template = f'''import uuid

from app.{entity_name}.{entity_name} import {entity_class}
from app.{entity_name}.api.schemas import Create{entity_class}Command, Update{entity_class}Command
from app.{entity_name}.repositories.{entity_name}_repository import {repository_class}
from app.events.{entity_name}.publisher import {publisher_class}
from infrastructure.database import Transactional


class {service_class}:
    def __init__(
        self,
        *,
        repository: {repository_class},
        event_publisher: {publisher_class},
    ) -> None:
        self.repository = repository
        self.event_publisher = event_publisher

    async def get_{entity_name}_list(
        self,
        *,
        limit: int = 12,
        prev: int | None = None,
    ) -> list[{entity_class}]:
        return await self.repository.get_{entity_name}s(limit=limit, prev=prev)

    @Transactional()
    async def create_{entity_name}(self, *, command: Create{entity_class}Command) -> {entity_class}:
        """Create a new {entity_name}"""
        {unique_validation}

        {entity_name} = {entity_class}.create(
            {', '.join(f'{field.name}=command.{field.name}' for field in fields)},
        )
        await self.repository.create_{entity_name}({entity_name}={entity_name})

        # Publish {entity_name} creation event
        await self.event_publisher.{entity_name}_created(
            {entity_name}_id=str({entity_name}.id),
            {entity_name}_data={{
{field_data_create_str}
            }},
        )

        return {entity_name}

    async def get_{entity_name}_by_id(self, *, {entity_name}_id: str) -> {entity_class} | None:
        {entity_name}_uuid = uuid.UUID({entity_name}_id)
        return await self.repository.get_{entity_name}_by_id({entity_name}_id={entity_name}_uuid)

    async def get_{entity_name}_by_id_with_relations(self, *, {entity_name}_id: str) -> {entity_class} | None:
        {entity_name}_uuid = uuid.UUID({entity_name}_id)
        return await self.repository.get_{entity_name}_by_id_with_relations({entity_name}_id={entity_name}_uuid)

    @Transactional()
    async def update_{entity_name}(self, *, command: Update{entity_class}Command) -> {entity_class} | None:
        """Update an existing {entity_name}"""
        {entity_name}_uuid = uuid.UUID(command.{entity_name}_id)
        {entity_name} = await self.repository.get_{entity_name}_by_id({entity_name}_id={entity_name}_uuid)
        if not {entity_name}:
            return None
{unique_check_update}

        # Update {entity_name} fields
        {field_data_update_str}

        await self.repository.update_{entity_name}({entity_name}={entity_name})

        # Publish {entity_name} update event
        await self.event_publisher.{entity_name}_updated(
            {entity_name}_id=str({entity_name}.id),
            {entity_name}_data={{
{field_data_create_str}
            }},
        )

        return {entity_name}

    @Transactional()
    async def delete_{entity_name}(self, *, {entity_name}_id: str) -> bool:
        """Delete a {entity_name} by ID"""
        {entity_name}_uuid = uuid.UUID({entity_name}_id)
        {entity_name} = await self.repository.get_{entity_name}_by_id({entity_name}_id={entity_name}_uuid)
        if not {entity_name}:
            return False

        await self.repository.delete_{entity_name}({entity_name}={entity_name})

        # Publish {entity_name} deletion event
        await self.event_publisher.{entity_name}_deleted({entity_name}_id={entity_name}_id)

        return True
'''
    return template


def generate_schemas_file(entity_name: str, fields: list[FieldDefinition]) -> str:
    """Generate Pydantic schemas file content"""
    entity_class = to_pascal_case(entity_name)

    pydantic_imports = get_pydantic_imports(fields)
    datetime_import = ""
    if 'datetime' in pydantic_imports:
        datetime_import = "from datetime import datetime\n"

    # Generate field definitions for request/response models
    create_fields = []
    update_fields = []
    response_fields = []
    command_fields = []
    update_command_fields = []

    for field in fields:
        python_type = TYPE_MAPPINGS[field.type_]['python']
        field_desc = f'"{field.name.replace("_", " ").title()}"'

        if field.optional:
            # Create request: optional with default None
            create_fields.append(f'    {field.name}: {python_type} | None = Field(None, description={field_desc})')
            # Update request: optional
            update_fields.append(f'    {field.name}: {python_type} | None = Field(None, description={field_desc})')
            # Response: optional
            response_fields.append(f'    {field.name}: {python_type} | None = Field(None, description={field_desc})')
            # Create command: optional with default None
            command_fields.append(f'    {field.name}: {python_type} | None = None')
            # Update command: required (will be filled in service)
            update_command_fields.append(f'    {field.name}: {python_type}')
        else:
            # Create request: required
            create_fields.append(f'    {field.name}: {python_type} = Field(..., description={field_desc})')
            # Update request: optional for partial updates
            update_fields.append(f'    {field.name}: {python_type} | None = Field(None, description={field_desc})')
            # Response: required
            response_fields.append(f'    {field.name}: {python_type} = Field(..., description={field_desc})')
            # Create command: required
            command_fields.append(f'    {field.name}: {python_type}')
            # Update command: required
            update_command_fields.append(f'    {field.name}: {python_type}')

    create_fields_str = '\n'.join(create_fields)
    update_fields_str = '\n'.join(update_fields)
    response_fields_str = '\n'.join(response_fields)
    command_fields_str = '\n'.join(command_fields)
    update_command_fields_str = '\n'.join(update_command_fields)

    template = f'''"""{entity_class} API schemas - consolidated request/response models"""

import uuid
{datetime_import}
from pydantic import BaseModel, ConfigDict, Field, field_validator


# Request Models
class Create{entity_class}Request(BaseModel):
    """{entity_class} creation request"""

{create_fields_str}


class Update{entity_class}Request(BaseModel):
    """{entity_class} update request"""

{update_fields_str}


# Response Models
class {entity_class}Response(BaseModel):
    """{entity_class} data response"""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="{entity_class} ID")
{response_fields_str}

    @field_validator("id", mode="before")
    @classmethod
    def validate_id(cls, v):
        """Convert UUID to string"""
        if isinstance(v, uuid.UUID):
            return str(v)
        return v


class Create{entity_class}Response(BaseModel):
    """{entity_class} creation response"""

    id: str = Field(..., description="{entity_class} ID")
    {fields[0].name}: {TYPE_MAPPINGS[fields[0].type_]['python']} = Field(..., description="{fields[0].name.replace("_", " ").title()}")

    @field_validator("id", mode="before")
    @classmethod
    def validate_id(cls, v):
        """Convert UUID to string"""
        if isinstance(v, uuid.UUID):
            return str(v)
        return v


# Command Models (for internal use)
class Create{entity_class}Command(BaseModel):
    """Internal command for {entity_name} creation"""

{command_fields_str}


class Update{entity_class}Command(BaseModel):
    """Internal command for {entity_name} updates"""

    {entity_name}_id: str
{update_command_fields_str}
'''
    return template


def generate_router_file(entity_name: str, fields: list[FieldDefinition]) -> str:
    """Generate FastAPI router file content"""
    entity_class = to_pascal_case(entity_name)
    service_class = f"{entity_class}Service"

    # Generate field assignments for update command in router
    update_field_assignments = []
    for field in fields:
        if field.optional:
            assignment = f'''            {field.name}=request.{field.name}
            if request.{field.name} is not None
            else current_{entity_name}.{field.name},'''
        else:
            assignment = f'''            {field.name}=request.{field.name}
            if request.{field.name} is not None
            else current_{entity_name}.{field.name},'''
        update_field_assignments.append(assignment)

    update_field_assignments_str = '\n'.join(update_field_assignments)

    template = f'''"""{entity_class} API routers - consolidated FastAPI endpoints"""

from app.{entity_name}.api.schemas import (
    {entity_class}Response,
    Create{entity_class}Command,
    Create{entity_class}Request,
    Create{entity_class}Response,
    Update{entity_class}Command,
    Update{entity_class}Request,
)
from app.{entity_name}.services.{entity_name}_service import {service_class}
from app.container import Container
from core.exceptions.domain import {entity_class}NotFound
from dependency_injector.wiring import Provide, inject
from fastapi.responses import Response

from fastapi import APIRouter, Depends, HTTPException, Query


{entity_name}_router = APIRouter()


@{entity_name}_router.get(
    "",
    response_model=list[{entity_class}Response],
    summary="Get list of {entity_name}s",
    description=f"""
    Retrieve a paginated list of all {entity_name}s in the system.

    **Parameters:**
    - **limit**: Maximum number of {entity_name}s to return (default: 10, max: 12)
    - **prev**: ID of the previous {entity_name} for pagination (optional)

    **Returns:**
    A list of {entity_name} objects with their basic information.
    """,
)
@inject
async def get_{entity_name}_list(
    limit: int = Query(10, description="Maximum number of {entity_name}s to return", ge=1, le=12),
    prev: int | None = Query(None, description="ID of the previous {entity_name} for pagination"),
    {entity_name}_service: {service_class} = Depends(Provide[Container.{entity_name}_service]),
) -> list[{entity_class}Response]:
    """Get paginated list of {entity_name}s with optional filtering"""
    {entity_name}s = await {entity_name}_service.get_{entity_name}_list(limit=limit, prev=prev)
    return [{entity_class}Response.model_validate({entity_name}) for {entity_name} in {entity_name}s]


@{entity_name}_router.post(
    "",
    response_model=Create{entity_class}Response,
    status_code=201,
    summary="Create a new {entity_name}",
    description=f"""
    Create a new {entity_name} in the system.

    **Required fields:**
    - **{fields[0].name}**: {fields[0].name.replace("_", " ").title()}

    **Returns:**
    The created {entity_name}'s basic information.
    """,
)
@inject
async def create_{entity_name}(
    request: Create{entity_class}Request,
    {entity_name}_service: {service_class} = Depends(Provide[Container.{entity_name}_service]),
) -> Create{entity_class}Response:
    """Create a new {entity_name} with the provided information"""
    command = Create{entity_class}Command(**request.model_dump())
    {entity_name} = await {entity_name}_service.create_{entity_name}(command=command)
    return Create{entity_class}Response(id={entity_name}.id, {fields[0].name}={entity_name}.{fields[0].name})


@{entity_name}_router.get(
    "/{{{entity_name}_id}}",
    response_model={entity_class}Response,
    summary="Get {entity_name} by ID",
    description=(
        "Retrieve a specific {entity_name} by ID with all relationships"
    ),
)
@inject
async def get_{entity_name}(
    {entity_name}_id: str,
    {entity_name}_service: {service_class} = Depends(Provide[Container.{entity_name}_service]),
) -> {entity_class}Response:
    """Get {entity_name} by ID with relationships"""
    {entity_name} = await {entity_name}_service.get_{entity_name}_by_id_with_relations({entity_name}_id={entity_name}_id)
    if not {entity_name}:
        raise {entity_class}NotFound
    return {entity_class}Response.model_validate({entity_name})


@{entity_name}_router.put(
    "/{{{entity_name}_id}}",
    response_model={entity_class}Response,
    summary="Update a {entity_name}",
    description=f"""
    Update an existing {entity_name}'s information.

    **Path parameter:**
    - **{entity_name}_id**: The ID of the {entity_name} to update

    **Request body:**
    - **{fields[0].name}**: Updated {fields[0].name.replace("_", " ")} (optional)

    **Returns:**
    The updated {entity_name}'s information.
    """,
)
@inject
async def update_{entity_name}(
    {entity_name}_id: str,
    request: Update{entity_class}Request,
    {entity_name}_service: {service_class} = Depends(Provide[Container.{entity_name}_service]),
) -> {entity_class}Response:
    """Update an existing {entity_name}"""
    try:
        # Get current {entity_name} to fill in missing fields
        current_{entity_name} = await {entity_name}_service.get_{entity_name}_by_id({entity_name}_id={entity_name}_id)
        if not current_{entity_name}:
            raise HTTPException(status_code=404, detail="{entity_class} not found")

        # Create command with current values as defaults for optional fields
        command = Update{entity_class}Command(
            {entity_name}_id={entity_name}_id,
{update_field_assignments_str}
        )

        updated_{entity_name} = await {entity_name}_service.update_{entity_name}(command=command)
        if not updated_{entity_name}:
            raise HTTPException(status_code=404, detail="{entity_class} not found")

        return {entity_class}Response.model_validate(updated_{entity_name})

    except HTTPException:
        raise
    except Exception as e:
        if "{entity_class}AlreadyExists" in str(e):
            raise HTTPException(
                status_code=409,
                detail="{entity_class} with this information already exists",
            ) from e
        raise


@{entity_name}_router.delete(
    "/{{{entity_name}_id}}",
    status_code=204,
    summary="Delete a {entity_name}",
    description=f"""
    Delete a {entity_name} and all related data (cascade delete).

    **Path parameter:**
    - **{entity_name}_id**: The ID of the {entity_name} to delete

    **Note:** This operation will also delete all related data.
    """,
)
@inject
async def delete_{entity_name}(
    {entity_name}_id: str,
    {entity_name}_service: {service_class} = Depends(Provide[Container.{entity_name}_service]),
) -> Response:
    """Delete a {entity_name} by ID"""
    success = await {entity_name}_service.delete_{entity_name}({entity_name}_id={entity_name}_id)
    if not success:
        raise HTTPException(status_code=404, detail="{entity_class} not found")
    return Response(status_code=204)
'''
    return template


def generate_event_events_file(entity_name: str, fields: list[FieldDefinition]) -> str:
    """Generate events.py file content"""
    entity_class = to_pascal_case(entity_name)

    template = f'''"""{entity_class} domain events"""

from dataclasses import dataclass
from typing import Any
from typing_extensions import TypedDict

from app.events.core.base import BaseEvent


class {entity_class}EventPayload(TypedDict):
    """Type for {entity_name} event payloads received by handlers"""

    entity_id: str
    event_type: str
    data: dict[str, Any]


@dataclass
class {entity_class}Event(BaseEvent):
    """{entity_class}-specific event"""

    @classmethod
    def created(cls, {entity_name}_id: str, {entity_name}_data: dict[str, Any]) -> "{entity_class}Event":
        """Create {entity_name} created event"""
        return cls(entity_id={entity_name}_id, event_type="created", data={entity_name}_data)

    @classmethod
    def updated(cls, {entity_name}_id: str, {entity_name}_data: dict[str, Any]) -> "{entity_class}Event":
        """Create {entity_name} updated event"""
        return cls(entity_id={entity_name}_id, event_type="updated", data={entity_name}_data)

    @classmethod
    def deleted(cls, {entity_name}_id: str) -> "{entity_class}Event":
        """Create {entity_name} deleted event"""
        return cls(entity_id={entity_name}_id, event_type="deleted", data={{}})
'''
    return template


def generate_event_publisher_file(entity_name: str, fields: list[FieldDefinition]) -> str:
    """Generate publisher.py file content"""
    entity_class = to_pascal_case(entity_name)

    template = f'''"""{entity_class} event publisher"""

from typing import Any

from app.events.core.base import BaseEventPublisher

from .events import {entity_class}Event


class {entity_class}EventPublisher(BaseEventPublisher):
    """Publisher for {entity_name} domain events"""

    def get_domain_prefix(self) -> str:
        return "{entity_name}"

    async def {entity_name}_created(self, {entity_name}_id: str, {entity_name}_data: dict[str, Any]) -> None:
        """Publish {entity_name} created event"""
        event = {entity_class}Event.created({entity_name}_id, {entity_name}_data)
        await self.publish_domain_event("created", event)

    async def {entity_name}_updated(self, {entity_name}_id: str, {entity_name}_data: dict[str, Any]) -> None:
        """Publish {entity_name} updated event"""
        event = {entity_class}Event.updated({entity_name}_id, {entity_name}_data)
        await self.publish_domain_event("updated", event)

    async def {entity_name}_deleted(self, {entity_name}_id: str) -> None:
        """Publish {entity_name} deleted event"""
        event = {entity_class}Event.deleted({entity_name}_id)
        await self.publish_domain_event("deleted", event)
'''
    return template


def generate_event_handlers_file(entity_name: str, fields: list[FieldDefinition]) -> str:
    """Generate handlers.py file content"""
    entity_class = to_pascal_case(entity_name)

    template = f'''"""{entity_class} event handlers"""

import logging

from app.{entity_name}.api.schemas import {entity_class}Response, Create{entity_class}Response
from app.events.core.registry import event_registry
from faststream.redis import RedisRouter


logger = logging.getLogger(__name__)

# Create {entity_name}-specific router
{entity_name}_router = RedisRouter()


@{entity_name}_router.subscriber("{entity_name}.created")
async def handle_{entity_name}_created(data: Create{entity_class}Response):
    """Handle {entity_name} created events"""
    logger.info(f"{entity_class} created: {{data.id}}")
    logger.debug(f"{entity_class} data: {{data.model_dump()}}")


@{entity_name}_router.subscriber("{entity_name}.updated")
async def handle_{entity_name}_updated(data: {entity_class}Response):
    """Handle {entity_name} updated events"""
    logger.info(f"{entity_class} updated: {{data.id}}")
    logger.debug(f"Updated data: {{data.model_dump()}}")


@{entity_name}_router.subscriber("{entity_name}.deleted")
async def handle_{entity_name}_deleted(data: dict):
    """Handle {entity_name} deleted events"""
    entity_id = data.get("entity_id")
    logger.info(f"{entity_class} deleted: {{entity_id}}")


# Register the router with the event registry
event_registry.register_domain_router("{entity_name}", {entity_name}_router)
'''
    return template


def check_existing_directories(directories: list[Path], force: bool = False) -> None:
    """Check if any directories already exist and handle conflicts

    Args:
        directories: List of directories to check
        force: If True, allow overwriting existing directories

    Raises:
        ValidationError: If directories exist and force is False
    """
    existing = [d for d in directories if d.exists()]

    if existing and not force:
        existing_paths = '\n'.join(f"  - {d}" for d in existing)
        raise ValidationError(
            f"The following directories already exist:\n{existing_paths}\n"
            "Use --force to overwrite or choose a different entity name"
        )


def write_file_content(file_path: Path, content: str, dry_run: bool = False) -> None:
    """Write content to a file

    Args:
        file_path: Path to write the file
        content: Content to write
        dry_run: If True, only print what would be written
    """
    if dry_run:
        print(f"Would create: {file_path}")
    else:
        file_path.write_text(content)
        print(f"📄 Generated: {file_path}")


def generate_all_files(entity_name: str, fields: list[FieldDefinition], dry_run: bool = False) -> None:
    """Generate all CRUD + Event files for the entity

    Args:
        entity_name: The entity name
        fields: List of field definitions
        dry_run: If True, only print what would be created
    """
    project_root = Path(__file__).parent.parent

    # Define all file paths
    files_to_generate = {
        # Model file
        project_root / "app" / entity_name / f"{entity_name}.py":
            generate_model_file(entity_name, fields),

        # Repository file
        project_root / "app" / entity_name / "repositories" / f"{entity_name}_repository.py":
            generate_repository_file(entity_name, fields),

        # Service file
        project_root / "app" / entity_name / "services" / f"{entity_name}_service.py":
            generate_service_file(entity_name, fields),

        # API files
        project_root / "app" / entity_name / "api" / "routers.py":
            generate_router_file(entity_name, fields),

        project_root / "app" / entity_name / "api" / "schemas.py":
            generate_schemas_file(entity_name, fields),

        # Event files
        project_root / "app" / "events" / entity_name / "events.py":
            generate_event_events_file(entity_name, fields),

        project_root / "app" / "events" / entity_name / "publisher.py":
            generate_event_publisher_file(entity_name, fields),

        project_root / "app" / "events" / entity_name / "handlers.py":
            generate_event_handlers_file(entity_name, fields),
    }

    # Generate all files
    for file_path, content in files_to_generate.items():
        write_file_content(file_path, content, dry_run)

    if not dry_run:
        print(f"\n✅ Generated {len(files_to_generate)} files for {entity_name}")
    else:
        print(f"\n✅ Would generate {len(files_to_generate)} files for {entity_name}")


def generate_init_files(entity_name: str, dry_run: bool = False) -> None:
    """Generate __init__.py files for proper Python package structure

    Args:
        entity_name: The entity name
        dry_run: If True, only print what would be created
    """
    project_root = Path(__file__).parent.parent

    init_files = [
        project_root / "app" / entity_name / "__init__.py",
        project_root / "app" / entity_name / "api" / "__init__.py",
        project_root / "app" / entity_name / "repositories" / "__init__.py",
        project_root / "app" / entity_name / "services" / "__init__.py",
        project_root / "app" / "events" / entity_name / "__init__.py",
    ]

    for init_file in init_files:
        write_file_content(init_file, "", dry_run)


# ==================== STAGE 3: CONTAINER INTEGRATION FUNCTIONS ====================

def add_domain_exceptions(entity_name: str, dry_run: bool = False) -> None:
    """Add domain exceptions for the entity to core/exceptions/domain.py

    Args:
        entity_name: The entity name
        dry_run: If True, only print what would be created
    """
    entity_class = to_pascal_case(entity_name)
    project_root = Path(__file__).parent.parent
    domain_exceptions_path = project_root / "core" / "exceptions" / "domain.py"

    if not domain_exceptions_path.exists():
        if dry_run:
            print(f"Would create: {domain_exceptions_path}")
            return
        else:
            raise ValidationError(f"Domain exceptions file not found: {domain_exceptions_path}")

    # Read current content
    content = domain_exceptions_path.read_text()

    # Check if exceptions already exist
    if f"class {entity_class}Exception" in content:
        if not dry_run:
            print(f"⚠️  Domain exceptions already exist for {entity_name}")
        return

    # Generate exception classes
    exception_content = f'''

class {entity_class}Exception(DomainException):
    """{entity_class}-related exceptions"""


class {entity_class}NotFound({entity_class}Exception):
    code = 404
    error_code = "{entity_name.upper()}_NOT_FOUND"
    message = "{entity_class} not found"


class {entity_class}AlreadyExists({entity_class}Exception):
    code = 409
    error_code = "{entity_name.upper()}_ALREADY_EXISTS"
    message = "{entity_class} already exists"
'''

    if dry_run:
        print(f"Would add domain exceptions for {entity_name} to {domain_exceptions_path}")
    else:
        # Append to end of file
        with domain_exceptions_path.open('a') as f:
            f.write(exception_content)
        print(f"✅ Added domain exceptions for {entity_name}")


def update_container_file(entity_name: str, dry_run: bool = False) -> None:
    """Update app/container.py to add providers for new entity

    Args:
        entity_name: The entity name
        dry_run: If True, only print what would be created
    """
    entity_class = to_pascal_case(entity_name)
    project_root = Path(__file__).parent.parent
    container_path = project_root / "app" / "container.py"

    if not container_path.exists():
        raise ValidationError(f"Container file not found: {container_path}")

    content = container_path.read_text()

    # Check if entity already integrated
    if f"{entity_name}_repository" in content:
        if not dry_run:
            print(f"⚠️  Container already configured for {entity_name}")
        return

    if dry_run:
        print(f"Would update container.py to add providers for {entity_name}")
        return

    # Add imports section
    import_lines = f"""from app.{entity_name}.repositories.{entity_name}_repository import {entity_class}Repository
from app.{entity_name}.services.{entity_name}_service import {entity_class}Service
from app.events.{entity_name}.publisher import {entity_class}EventPublisher"""

    # Find import insertion point (after existing agent imports)
    agent_import_line = "from app.agents.services.agent_service import AgentService"
    import_insertion_point = content.find(agent_import_line)

    if import_insertion_point == -1:
        raise ValidationError("Could not find import insertion point in container.py")

    # Insert imports after AgentService import
    import_end = content.find('\n', import_insertion_point) + 1
    content = content[:import_end] + import_lines + '\n' + content[import_end:]

    # Add event publisher (after existing event publishers)
    event_publisher_code = f'''
    {entity_name}_event_publisher = providers.Singleton(
        {entity_class}EventPublisher,
        broker=broker,
    )
'''

    # Find event publisher insertion point
    webhook_publisher = "webhook_event_publisher = providers.Singleton("
    publisher_insertion_point = content.find(webhook_publisher)

    if publisher_insertion_point != -1:
        # Find the end of webhook_event_publisher block
        publisher_end = content.find(')', publisher_insertion_point)
        publisher_end = content.find('\n', publisher_end) + 1
        content = content[:publisher_end] + event_publisher_code + content[publisher_end:]

    # Add repository and service providers (after existing ones)
    providers_code = f'''
    # {entity_class} providers
    {entity_name}_repository = providers.Factory({entity_class}Repository)

    {entity_name}_service = providers.Singleton(
        {entity_class}Service,
        repository={entity_name}_repository,
        event_publisher={entity_name}_event_publisher,
    )
'''

    # Find service insertion point (after agent_service)
    agent_service_line = "agent_service = providers.Singleton("
    service_insertion_point = content.find(agent_service_line)

    if service_insertion_point != -1:
        # Find the end of agent_service block
        service_end = content.find(')', service_insertion_point)
        service_end = content.find('\n', service_end) + 1
        content = content[:service_end] + providers_code + content[service_end:]

    # Write updated content
    container_path.write_text(content)
    print(f"✅ Updated container.py with {entity_name} providers")


def update_server_file(entity_name: str, dry_run: bool = False) -> None:
    """Update app/server.py to include new router

    Args:
        entity_name: The entity name
        dry_run: If True, only print what would be created
    """
    project_root = Path(__file__).parent.parent
    server_path = project_root / "app" / "server.py"

    if not server_path.exists():
        raise ValidationError(f"Server file not found: {server_path}")

    content = server_path.read_text()

    # Check if router already added
    if f"{entity_name}_router" in content:
        if not dry_run:
            print(f"⚠️  Server already configured for {entity_name}")
        return

    if dry_run:
        print(f"Would update server.py to include {entity_name}_router")
        return

    # Add router import
    router_import = f"from app.{entity_name}.api.routers import {entity_name}_router"

    # Find import insertion point (after webhook_router import)
    webhook_import = "from app.webhooks.api.routers import webhook_router"
    import_insertion_point = content.find(webhook_import)

    if import_insertion_point != -1:
        import_end = content.find('\n', import_insertion_point) + 1
        content = content[:import_end] + router_import + '\n' + content[import_end:]

    # Add router to setup_routes function
    entity_plural = get_table_name(entity_name)
    router_line = f'    app.include_router({entity_name}_router, prefix="/api/v1/{entity_plural}")'

    # Find setup_routes function and webhook router line
    webhook_router_line = 'app.include_router(webhook_router, prefix="/api/v1")'
    router_insertion_point = content.find(webhook_router_line)

    if router_insertion_point != -1:
        router_end = content.find('\n', router_insertion_point) + 1
        content = content[:router_end] + router_line + '\n' + content[router_end:]

    # Add module to container wiring
    wiring_module = f'"app.{entity_name}.api.routers",'

    # Find container.wire section
    wire_modules_start = content.find('container.wire(')
    modules_start = content.find('modules=[', wire_modules_start)
    webhook_module = '"app.webhooks.api.routers",'
    webhook_insertion_point = content.find(webhook_module)

    if webhook_insertion_point != -1:
        webhook_end = content.find('\n', webhook_insertion_point) + 1
        # Insert before the closing bracket, maintaining indentation
        content = content[:webhook_end] + f"            {wiring_module}\n" + content[webhook_end:]

    # Write updated content
    server_path.write_text(content)
    print(f"✅ Updated server.py with {entity_name}_router")


def integrate_with_system(entity_name: str, dry_run: bool = False) -> None:
    """Orchestrate all system integration tasks

    Args:
        entity_name: The entity name
        dry_run: If True, only print what would be done
    """
    print(f"🔧 Stage 3: Integrating {entity_name} with container and server...")

    # Step 1: Add domain exceptions
    add_domain_exceptions(entity_name, dry_run)

    # Step 2: Update container.py
    update_container_file(entity_name, dry_run)

    # Step 3: Update server.py
    update_server_file(entity_name, dry_run)

    if not dry_run:
        print(f"✅ Stage 3 complete: {entity_name} integrated with system")
    else:
        print(f"✅ Stage 3 dry-run complete: Would integrate {entity_name} with system")


def generate_migration_file(entity_name: str, fields: list[FieldDefinition], dry_run: bool = False) -> None:
    """Generate Alembic migration file for new entity

    Args:
        entity_name: The entity name
        fields: List of field definitions
        dry_run: If True, only print what would be created
    """
    entity_class = to_pascal_case(entity_name)
    table_name = get_table_name(entity_name)
    project_root = Path(__file__).parent.parent

    # Generate timestamp and revision ID
    from datetime import datetime
    import secrets
    import subprocess

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    revision_id = secrets.token_hex(6)

    migration_file = f"{timestamp}_add_{entity_name}_table.py"
    migrations_dir = project_root / "alembic" / "versions"
    migration_path = migrations_dir / migration_file

    if dry_run:
        print(f"Would create migration: {migration_file}")
        return

    # Get current head revision
    current_head = None
    try:
        result = subprocess.run(
            ["poetry", "run", "alembic", "current"],
            cwd=project_root,
            capture_output=True,
            text=True,
            check=True
        )
        # Extract revision ID from output like "86134d8125b5 (head)"
        if result.stdout.strip():
            current_head = result.stdout.strip().split()[0]
    except subprocess.CalledProcessError:
        print("⚠️  Could not get current head, creating initial migration")
        current_head = None

    # Build column definitions
    column_defs = []
    import_lines = ["import sqlalchemy as sa"]

    for field in fields:
        if field.name in ['id', 'created_at', 'updated_at']:
            continue  # Skip base model fields

        col_type = get_sqlalchemy_column_type(field.type_)
        nullable = "True" if field.optional else "False"

        if field.type_ == "uuid":
            if "import uuid" not in import_lines:
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
            elif field.type_ == "uuid":
                if field.default == "uuid4":
                    default_part = f", default=uuid.uuid4"

        column_def = f"    sa.Column('{field.name}', {col_type}, nullable={nullable}{default_part})"

        column_defs.append(column_def)

    imports_str = "\n".join(import_lines)
    columns_str = ",\n".join(column_defs)

    migration_content = f'''"""{entity_class} table

Revision ID: {revision_id}
Revises: {current_head or ''}
Create Date: {datetime.now().isoformat()}

"""
from alembic import op
{imports_str}


# revision identifiers, used by Alembic.
revision = '{revision_id}'
down_revision = {repr(current_head)}
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

    migration_path.write_text(migration_content)
    print(f"✅ Migration created: {migration_file}")


def get_sqlalchemy_column_type(field_type: str) -> str:
    """Convert field type to SQLAlchemy column type"""
    type_mapping = {
        "str": "sa.String(255)",
        "text": "sa.Text()",
        "int": "sa.Integer()",
        "float": "sa.Float()",
        "bool": "sa.Boolean()",
        "datetime": "sa.DateTime()",
        "date": "sa.Date()",
        "time": "sa.Time()",
        "uuid": "sa.UUID()",
        "json": "sa.JSON()",
        "decimal": "sa.Numeric(precision=10, scale=2)",
    }

    return type_mapping.get(field_type, "sa.String(255)")


def run_migration(entity_name: str, dry_run: bool = False) -> None:
    """Run the generated migration using Alembic

    Args:
        entity_name: The entity name
        dry_run: If True, only print what would be run
    """
    if dry_run:
        print(f"Would run: poetry run alembic upgrade head")
        return

    import subprocess

    project_root = Path(__file__).parent.parent

    try:
        # Run migration
        result = subprocess.run(
            ["poetry", "run", "alembic", "upgrade", "head"],
            cwd=project_root,
            capture_output=True,
            text=True,
            check=True
        )
        print(f"✅ Migration applied successfully for {entity_name}")
        if result.stdout:
            print(f"Output: {result.stdout.strip()}")

    except subprocess.CalledProcessError as e:
        print(f"❌ Migration failed: {e.stderr}")
        raise ValidationError(f"Failed to run migration: {e.stderr}")


def generate_crud_with_transaction(entity_name: str, fields: list[FieldDefinition], force: bool = False) -> None:
    """Generate CRUD with transaction rollback support

    Args:
        entity_name: The entity name
        fields: List of field definitions
        force: Whether to overwrite existing files

    Raises:
        CRUDGenerationError: If generation fails
    """
    try:
        # Import here to avoid circular imports
        from crud_transaction import CRUDTransaction

        with CRUDTransaction(entity_name, fields) as transaction:
            print(f"🚀 Generating CRUD for entity: {entity_name} (with rollback support)")

            # Stage 1: Create directory structure
            print("\n📁 Creating directory structure...")
            directories = get_directory_structure(entity_name)
            for directory in directories:
                transaction.create_directory(directory)

            # Create __init__.py files
            project_root = Path(__file__).parent.parent
            init_files = [
                project_root / "app" / entity_name / "__init__.py",
                project_root / "app" / entity_name / "api" / "__init__.py",
                project_root / "app" / entity_name / "repositories" / "__init__.py",
                project_root / "app" / entity_name / "services" / "__init__.py",
                project_root / "app" / "events" / entity_name / "__init__.py",
            ]

            for init_file in init_files:
                transaction.create_file(init_file, "")

            # Stage 2: Generate all CRUD files
            print(f"\n📄 Stage 2: Generating CRUD + Event files...")

            # Generate all files using transaction
            files_to_generate = {
                # Model file
                project_root / "app" / entity_name / f"{entity_name}.py":
                    generate_model_file(entity_name, fields),

                # Repository file
                project_root / "app" / entity_name / "repositories" / f"{entity_name}_repository.py":
                    generate_repository_file(entity_name, fields),

                # Service file
                project_root / "app" / entity_name / "services" / f"{entity_name}_service.py":
                    generate_service_file(entity_name, fields),

                # API files
                project_root / "app" / entity_name / "api" / "routers.py":
                    generate_router_file(entity_name, fields),

                project_root / "app" / entity_name / "api" / "schemas.py":
                    generate_schemas_file(entity_name, fields),

                # Event files
                project_root / "app" / "events" / entity_name / "events.py":
                    generate_event_events_file(entity_name, fields),

                project_root / "app" / "events" / entity_name / "publisher.py":
                    generate_event_publisher_file(entity_name, fields),

                project_root / "app" / "events" / entity_name / "handlers.py":
                    generate_event_handlers_file(entity_name, fields),
            }

            # Create all files using transaction
            for file_path, content in files_to_generate.items():
                transaction.create_file(file_path, content)

            print(f"✅ Stage 2 complete: Generated {len(files_to_generate)} files")

            # Stage 3: System integration
            print(f"\n🔧 Stage 3: Integrating {entity_name} with container and server...")

            # Update domain exceptions
            transaction.modify_file_content(
                Path("core/exceptions/domain.py"),
                lambda content: _add_domain_exceptions_to_content(content, entity_name)
            )

            # Update container.py
            transaction.modify_file_content(
                Path("app/container.py"),
                lambda content: _update_container_content(content, entity_name)
            )

            # Update server.py
            transaction.modify_file_content(
                Path("app/server.py"),
                lambda content: _update_server_content(content, entity_name)
            )

            print(f"✅ Stage 3 complete: {entity_name} integrated with system")

            # Stage 4: Database migration
            print(f"\n🚀 Stage 4: Generating database migration for {entity_name}...")
            transaction.run_database_migration()
            print(f"✅ Stage 4 complete: Database migration for {entity_name}")

            # If we get here, everything succeeded
            transaction.commit()
            print(f"\n🎉 Successfully generated CRUD for {entity_name} with rollback support!")
            print("🔧 Next: Test generation (Stage 5)")

    except Exception as e:
        print(f"❌ CRUD generation failed: {e}")
        print("🔄 All changes have been automatically rolled back")
        raise


def run_stage_4(entity_name: str, fields: list[FieldDefinition], dry_run: bool = False) -> None:
    """Stage 4: Generate and run database migration

    Args:
        entity_name: The entity name
        fields: List of field definitions
        dry_run: If True, only print what would be done
    """
    if not dry_run:
        print(f"\n🚀 Stage 4: Generating database migration for {entity_name}...")
    else:
        print(f"\n🧪 Stage 4 (dry-run): Database migration for {entity_name}...")

    # Generate migration file
    generate_migration_file(entity_name, fields, dry_run)

    # Apply migration
    if not dry_run:
        run_migration(entity_name, dry_run)

    if not dry_run:
        print(f"✅ Stage 4 complete: Database migration for {entity_name}")
    else:
        print(f"✅ Stage 4 dry-run complete: Would generate and run migration for {entity_name}")


def _add_domain_exceptions_to_content(content: str, entity_name: str) -> str:
    """Add domain exceptions to the domain.py content"""
    entity_class = to_pascal_case(entity_name)

    # Check if exceptions already exist
    if f"class {entity_class}Exception" in content:
        return content  # Already exists, no changes needed

    # Generate exception classes
    exception_content = f'''

class {entity_class}Exception(DomainException):
    """{entity_class}-related exceptions"""


class {entity_class}NotFound({entity_class}Exception):
    code = 404
    error_code = "{entity_name.upper()}_NOT_FOUND"
    message = "{entity_class} not found"


class {entity_class}AlreadyExists({entity_class}Exception):
    code = 409
    error_code = "{entity_name.upper()}_ALREADY_EXISTS"
    message = "{entity_class} already exists"
'''

    # Append to end of file
    return content + exception_content


def _update_container_content(content: str, entity_name: str) -> str:
    """Update container.py content to add providers"""
    entity_class = to_pascal_case(entity_name)

    # Check if entity already integrated
    if f"{entity_name}_repository" in content:
        return content  # Already integrated, no changes needed

    # Add imports section
    import_lines = f"""from app.{entity_name}.repositories.{entity_name}_repository import {entity_class}Repository
from app.{entity_name}.services.{entity_name}_service import {entity_class}Service
from app.events.{entity_name}.publisher import {entity_class}EventPublisher"""

    # Find import insertion point (after existing agent imports)
    agent_import_line = "from app.agents.services.agent_service import AgentService"
    import_insertion_point = content.find(agent_import_line)

    if import_insertion_point == -1:
        raise ValueError("Could not find import insertion point in container.py")

    # Insert imports after AgentService import
    import_end = content.find('\n', import_insertion_point) + 1
    content = content[:import_end] + import_lines + '\n' + content[import_end:]

    # Add event publisher (after existing event publishers)
    event_publisher_code = f'''
    {entity_name}_event_publisher = providers.Singleton(
        {entity_class}EventPublisher,
        broker=broker,
    )
'''

    # Find event publisher insertion point
    webhook_publisher = "webhook_event_publisher = providers.Singleton("
    publisher_insertion_point = content.find(webhook_publisher)

    if publisher_insertion_point != -1:
        # Find the end of webhook_event_publisher block
        publisher_end = content.find(')', publisher_insertion_point)
        publisher_end = content.find('\n', publisher_end) + 1
        content = content[:publisher_end] + event_publisher_code + content[publisher_end:]

    # Add repository and service providers (after existing ones)
    providers_code = f'''
    # {entity_class} providers
    {entity_name}_repository = providers.Factory({entity_class}Repository)

    {entity_name}_service = providers.Singleton(
        {entity_class}Service,
        repository={entity_name}_repository,
        event_publisher={entity_name}_event_publisher,
    )
'''

    # Find service insertion point (after agent_service)
    agent_service_line = "agent_service = providers.Singleton("
    service_insertion_point = content.find(agent_service_line)

    if service_insertion_point != -1:
        # Find the end of agent_service block
        service_end = content.find(')', service_insertion_point)
        service_end = content.find('\n', service_end) + 1
        content = content[:service_end] + providers_code + content[service_end:]

    return content


def _update_server_content(content: str, entity_name: str) -> str:
    """Update server.py content to include new router"""
    # Check if router already added
    if f"{entity_name}_router" in content:
        return content  # Already added, no changes needed

    # Add router import
    router_import = f"from app.{entity_name}.api.routers import {entity_name}_router"

    # Find import insertion point (after webhook_router import)
    webhook_import = "from app.webhooks.api.routers import webhook_router"
    import_insertion_point = content.find(webhook_import)

    if import_insertion_point != -1:
        import_end = content.find('\n', import_insertion_point) + 1
        content = content[:import_end] + router_import + '\n' + content[import_end:]

    # Add router to setup_routes function
    entity_plural = get_table_name(entity_name)
    router_line = f'    app.include_router({entity_name}_router, prefix="/api/v1/{entity_plural}")'

    # Find setup_routes function and webhook router line
    webhook_router_line = 'app.include_router(webhook_router, prefix="/api/v1")'
    router_insertion_point = content.find(webhook_router_line)

    if router_insertion_point != -1:
        router_end = content.find('\n', router_insertion_point) + 1
        content = content[:router_end] + router_line + '\n' + content[router_end:]

    # Add module to container wiring
    wiring_module = f'"app.{entity_name}.api.routers",'

    # Find container.wire section
    webhook_module = '"app.webhooks.api.routers",'
    webhook_insertion_point = content.find(webhook_module)

    if webhook_insertion_point != -1:
        webhook_end = content.find('\n', webhook_insertion_point) + 1
        # Insert before the closing bracket, maintaining indentation
        content = content[:webhook_end] + f"            {wiring_module}\n" + content[webhook_end:]

    return content


def main() -> None:
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Generate CRUD boilerplate for FastAPI + SQLAlchemy + Events project",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/generate_crud.py --entity users --fields "name:str,email:str,is_active:bool"
  python scripts/generate_crud.py --entity products --fields "title:str,price:float,description:str?" --dry-run
  python scripts/generate_crud.py --entity orders --fields "amount:float,status:str" --force
  python scripts/generate_crud.py --entity posts --fields "title:str,content:text" --with-rollback
        """
    )

    parser.add_argument(
        '--entity',
        required=True,
        help='Entity name in snake_case (e.g., users, products, order_items)'
    )

    parser.add_argument(
        '--fields',
        required=True,
        help='Comma-separated field definitions (e.g., "name:str,email:str,is_active:bool,description:str?")'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be created without actually creating files/directories'
    )

    parser.add_argument(
        '--force',
        action='store_true',
        help='Overwrite existing files and directories'
    )

    parser.add_argument(
        '--with-rollback',
        action='store_true',
        help='Use transaction system with automatic rollback on failure (recommended for production)'
    )

    args = parser.parse_args()

    try:
        # Stage 1: Validation
        print(f"🚀 Generating CRUD for entity: {args.entity}")

        # Validate entity name (allow existing if force mode is enabled)
        validated_entity = validate_entity_name(args.entity, allow_existing=args.force)

        # Parse and validate fields
        fields = parse_fields(args.fields)
        field_summary = ', '.join(f"{f.name}:{f.type_}{'?' if f.optional else ''}" for f in fields)
        print(f"📝 Fields: {field_summary}")

        # Get directory structure
        directories = get_directory_structure(validated_entity)

        # Check for existing directories (unless force or dry-run)
        if not args.dry_run and not args.with_rollback:
            check_existing_directories(directories, force=args.force)

        # Choose generation method based on rollback option
        if args.dry_run:
            print("\n🔍 Dry-run mode - showing what would be created:")
            create_directories(directories, dry_run=True)
            generate_init_files(validated_entity, dry_run=True)
            print(f"\n📄 Stage 2: Template generation")
            generate_all_files(validated_entity, fields, dry_run=True)
            print(f"\n📄 Stage 3: Container integration (dry-run)")
            integrate_with_system(validated_entity, dry_run=True)
            print(f"\n📄 Stage 4: Database migration (dry-run)")
            run_stage_4(validated_entity, fields, dry_run=True)
            print(f"\n✅ Dry-run complete: Would create {len(directories)} directories, 13 files, and 1 migration")
        elif args.with_rollback:
            # Use new transaction-based generation
            generate_crud_with_transaction(validated_entity, fields, force=args.force)
        else:
            # Use original generation method
            print("\n📁 Creating directory structure:")
            create_directories(directories, dry_run=False)
            generate_init_files(validated_entity, dry_run=False)

            print(f"\n📄 Stage 2: Generating CRUD + Event files...")
            generate_all_files(validated_entity, fields, dry_run=False)

            print(f"\n✅ Stage 2 complete: Generated all CRUD + Event files")

            # Stage 3: Container Integration
            integrate_with_system(validated_entity, dry_run=False)

            # Stage 4: Database Migration
            run_stage_4(validated_entity, fields, dry_run=False)

            print("🔧 Next: Test generation (Stage 5)")

    except ValidationError as e:
        print(f"❌ Validation error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
