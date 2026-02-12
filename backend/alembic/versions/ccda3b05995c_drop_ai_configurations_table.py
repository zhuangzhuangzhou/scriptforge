"""drop_ai_configurations_table

Revision ID: ccda3b05995c
Revises: 20260211_ai_resource_plot
Create Date: 2026-02-12 01:09:51.620584

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'ccda3b05995c'
down_revision: Union[str, None] = '20260211_ai_resource_plot'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 删除 ai_configurations 表（已合并到 ai_resources）
    op.drop_index('ix_ai_configurations_category', table_name='ai_configurations')
    op.drop_index('ix_ai_configurations_key', table_name='ai_configurations')
    op.drop_index('ix_ai_configurations_user_id', table_name='ai_configurations')
    op.drop_table('ai_configurations')


def downgrade() -> None:
    # 恢复 ai_configurations 表
    op.create_table('ai_configurations',
        sa.Column('id', sa.UUID(), autoincrement=False, nullable=False),
        sa.Column('key', sa.VARCHAR(length=100), autoincrement=False, nullable=False),
        sa.Column('value', postgresql.JSONB(astext_type=sa.Text()), autoincrement=False, nullable=False),
        sa.Column('description', sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=True),
        sa.Column('updated_at', postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=True),
        sa.Column('user_id', sa.UUID(), autoincrement=False, nullable=True),
        sa.Column('category', sa.VARCHAR(length=50), autoincrement=False, nullable=True),
        sa.Column('is_active', sa.BOOLEAN(), autoincrement=False, nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='ai_configurations_user_id_fkey'),
        sa.PrimaryKeyConstraint('id', name='ai_configurations_pkey'),
        sa.UniqueConstraint('user_id', 'key', name='_user_key_uc')
    )
    op.create_index('ix_ai_configurations_user_id', 'ai_configurations', ['user_id'], unique=False)
    op.create_index('ix_ai_configurations_key', 'ai_configurations', ['key'], unique=False)
    op.create_index('ix_ai_configurations_category', 'ai_configurations', ['category'], unique=False)
