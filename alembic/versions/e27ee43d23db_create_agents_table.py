"""create_agents_table

Revision ID: e27ee43d23db
Revises: 729532316381
Create Date: 2025-09-24 15:03:55.684603

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e27ee43d23db'
down_revision: Union[str, None] = '729532316381'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create agents table with all current fields including llm_model and default_language
    op.create_table('agents',
        sa.Column('id', sa.UUID(), nullable=False, default=sa.text('uuid_generate_v4()')),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('phone_number', sa.String(length=255), nullable=False),
        sa.Column('description', sa.String(length=1000), nullable=True),
        sa.Column('instructions', sa.JSON(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=False),
        sa.Column('llm_model', sa.String(length=100), nullable=True),
        sa.Column('default_language', sa.String(length=10), nullable=True, server_default='pt-BR'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('phone_number')
    )

    # Create index for performance on common queries
    op.create_index('ix_agents_is_active', 'agents', ['is_active'])
    op.create_index('ix_agents_created_at', 'agents', ['created_at'])

    # Create trigger for auto-updating updated_at
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ language 'plpgsql';
    """)

    op.execute("""
        CREATE TRIGGER update_agents_updated_at 
        BEFORE UPDATE ON agents 
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    """)


def downgrade() -> None:
    # Drop trigger and function
    op.execute('DROP TRIGGER IF EXISTS update_agents_updated_at ON agents;')
    op.execute('DROP FUNCTION IF EXISTS update_updated_at_column();')
    
    # Drop indexes
    op.drop_index('ix_agents_created_at', table_name='agents')
    op.drop_index('ix_agents_is_active', table_name='agents')
    
    # Drop table
    op.drop_table('agents')
