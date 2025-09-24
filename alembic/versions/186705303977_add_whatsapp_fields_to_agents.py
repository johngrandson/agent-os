"""add_whatsapp_fields_to_agents

Revision ID: 186705303977
Revises: 491568791c88
Create Date: 2025-09-23 15:21:04.702936

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "186705303977"
down_revision: str | None = "491568791c88"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add WhatsApp fields to agents table
    op.add_column(
        "agents",
        sa.Column("whatsapp_enabled", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column("agents", sa.Column("whatsapp_token", sa.String(length=500), nullable=True))


def downgrade() -> None:
    # Remove WhatsApp fields from agents table
    op.drop_column("agents", "whatsapp_token")
    op.drop_column("agents", "whatsapp_enabled")
