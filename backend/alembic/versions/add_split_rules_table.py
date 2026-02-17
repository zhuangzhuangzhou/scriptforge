"""添加拆分规则表

Revision ID: add_split_rules_table
Revises:
Create Date: 2026-02-17 11:30:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'add_split_rules_table'
down_revision: Union[str, None] = '20260216_plot_points_raw'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'split_rules',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('display_name', sa.String(length=255), nullable=False),
        sa.Column('pattern', sa.Text(), nullable=False),
        sa.Column('pattern_type', sa.String(length=50), nullable=True),
        sa.Column('example', sa.Text(), nullable=True),
        sa.Column('is_default', sa.Boolean(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_split_rules_name', 'split_rules', ['name'], unique=True)


def downgrade() -> None:
    op.drop_index('ix_split_rules_name', table_name='split_rules')
    op.drop_table('split_rules')
