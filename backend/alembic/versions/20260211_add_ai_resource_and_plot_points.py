"""添加 ai_resources 表和 plot_breakdowns 新字段

Revision ID: 20260211_ai_resource_plot
Revises: 20260211_add_simple_agent, 8c01ccdeebaf
Create Date: 2026-02-11 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20260211_ai_resource_plot'
down_revision: Union[str, Sequence[str]] = ('20260211_add_simple_agent', '8c01ccdeebaf')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. 创建 ai_resources 表
    op.create_table(
        'ai_resources',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('display_name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('category', sa.String(length=50), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('is_builtin', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('owner_id', sa.UUID(), nullable=True),
        sa.Column('visibility', sa.String(length=20), nullable=True, server_default='public'),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('version', sa.Integer(), nullable=True, server_default='1'),
        sa.Column('parent_id', sa.UUID(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id']),
        sa.ForeignKeyConstraint(['parent_id'], ['ai_resources.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ai_resources_name'), 'ai_resources', ['name'])
    op.create_index(op.f('ix_ai_resources_category'), 'ai_resources', ['category'])
    op.create_index(op.f('ix_ai_resources_owner_id'), 'ai_resources', ['owner_id'])

    # 2. 给 plot_breakdowns 表添加新字段
    op.add_column('plot_breakdowns', sa.Column('plot_points', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('plot_breakdowns', sa.Column('format_version', sa.Integer(), nullable=True, server_default='1'))
    op.add_column('plot_breakdowns', sa.Column('qa_score', sa.Integer(), nullable=True))
    op.add_column('plot_breakdowns', sa.Column('qa_retry_count', sa.Integer(), nullable=True, server_default='0'))


def downgrade() -> None:
    # 删除 plot_breakdowns 新字段
    op.drop_column('plot_breakdowns', 'qa_retry_count')
    op.drop_column('plot_breakdowns', 'qa_score')
    op.drop_column('plot_breakdowns', 'format_version')
    op.drop_column('plot_breakdowns', 'plot_points')

    # 删除 ai_resources 表
    op.drop_index(op.f('ix_ai_resources_owner_id'), table_name='ai_resources')
    op.drop_index(op.f('ix_ai_resources_category'), table_name='ai_resources')
    op.drop_index(op.f('ix_ai_resources_name'), table_name='ai_resources')
    op.drop_table('ai_resources')
