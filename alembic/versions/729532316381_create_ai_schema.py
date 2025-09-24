"""create_ai_schema

Revision ID: 729532316381
Revises: ae657b67c7e7
Create Date: 2025-09-24 15:03:19.162638

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "729532316381"
down_revision: Union[str, None] = "ae657b67c7e7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create AI schema for Agno integration
    op.execute("CREATE SCHEMA IF NOT EXISTS ai;")
    op.execute("GRANT ALL ON SCHEMA ai TO CURRENT_USER;")
    op.execute("GRANT USAGE ON SCHEMA ai TO PUBLIC;")


def downgrade() -> None:
    # Drop AI schema
    op.execute("DROP SCHEMA IF EXISTS ai CASCADE;")
