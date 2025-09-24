"""create_ai_schema

Revision ID: 729532316381
Revises: ae657b67c7e7
Create Date: 2025-09-24 15:03:19.162638

"""

from collections.abc import Sequence

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "729532316381"
down_revision: str | None = "ae657b67c7e7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create AI schema for Agno integration
    op.execute("CREATE SCHEMA IF NOT EXISTS ai;")
    op.execute("GRANT ALL ON SCHEMA ai TO CURRENT_USER;")
    op.execute("GRANT USAGE ON SCHEMA ai TO PUBLIC;")


def downgrade() -> None:
    # Drop AI schema
    op.execute("DROP SCHEMA IF EXISTS ai CASCADE;")
