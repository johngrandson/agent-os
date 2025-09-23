"""setup ai schema for agentOS

Revision ID: 491568791c88
Revises: c5f8a9d2e1b6
Create Date: 2025-09-22 23:56:02.507864

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "491568791c88"
down_revision: Union[str, None] = "c5f8a9d2e1b6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create AI schema for AgentOS/Agno
    op.execute("CREATE SCHEMA IF NOT EXISTS ai")

    # Create vector extension in AI schema
    op.execute("CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA ai")

    # Grant permissions to fastapi user
    op.execute("GRANT ALL PRIVILEGES ON SCHEMA ai TO fastapi")


def downgrade() -> None:
    # Drop the AI schema and all its contents
    op.execute("DROP SCHEMA IF EXISTS ai CASCADE")
