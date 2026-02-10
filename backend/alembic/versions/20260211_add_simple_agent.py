"""添加 SimpleAgent 模型

Revision ID: 20260211_add_simple_agent
Revises: 20260211_extend_skill
Create Date: 2026-02-11 00:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20260211_add_simple_agent'
down_revision: Union[str, None] = '20260211_extend_skill'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 创建 simple_agents 表
    op.create_table(
        'simple_agents',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('display_name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('category', sa.String(length=50), nullable=True),
        sa.Column('workflow', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('is_builtin', sa.Boolean(), nullable=True, default=False),
        sa.Column('visibility', sa.String(length=20), nullable=True, default='public'),
        sa.Column('owner_id', sa.UUID(), nullable=False),
        sa.Column('version', sa.String(length=20), nullable=True, default='1.0.0'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_simple_agents_name'), 'simple_agents', ['name'], unique=True)


def downgrade() -> None:
    # 删除表
    op.drop_index(op.f('ix_simple_agents_name'), table_name='simple_agents')
    op.drop_table('simple_agents')
