"""add_knowledge_config_to_agents

Revision ID: c5f8a9d2e1b6
Revises: 986bab53fb5b
Create Date: 2025-09-22 18:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "c5f8a9d2e1b6"
down_revision: Union[str, None] = "986bab53fb5b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add knowledge_config field to agents table
    op.add_column(
        "agents",
        sa.Column(
            "knowledge_config", postgresql.JSON(astext_type=sa.Text()), nullable=True
        ),
    )


def downgrade() -> None:
    # Remove knowledge_config field from agents table
    op.drop_column("agents", "knowledge_config")
