"""add user tier and quota system

Revision ID: add_user_tier_system
Revises: add_agent_system
Create Date: 2026-02-04

新增用户等级和配额系统，支持：
- 用户分级：free(免费版), creator(创作者版), studio(工作室版), enterprise(企业版)
- 算力积分：用于按量计费
- 月度配额：限制每月产出剧集数
- 企业版自定义 API Key
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'add_user_tier_system'
down_revision = 'add_agent_system'
branch_labels = None
depends_on = None


def upgrade():
    # 用户等级: free(免费版), creator(创作者版), studio(工作室版), enterprise(企业版)
    op.add_column('users', sa.Column('tier', sa.String(20), nullable=False, server_default='free'))

    # 算力积分余额（用于按量计费）
    op.add_column('users', sa.Column('credits', sa.Integer, server_default='0'))

    # 本月已使用的剧集数（用于配额限制）
    op.add_column('users', sa.Column('monthly_episodes_used', sa.Integer, server_default='0'))

    # 配额重置时间（每月1号自动重置）
    op.add_column('users', sa.Column('monthly_reset_at', sa.TIMESTAMP(timezone=True)))

    # 用户自定义 API Key 配置（企业版功能）
    # 格式: {"openai": "sk-xxx", "claude": "sk-xxx"}
    op.add_column('users', sa.Column('api_keys', postgresql.JSON))

    # 创建索引以加速按等级查询
    op.create_index('idx_users_tier', 'users', ['tier'])


def downgrade():
    op.drop_index('idx_users_tier', table_name='users')
    op.drop_column('users', 'api_keys')
    op.drop_column('users', 'monthly_reset_at')
    op.drop_column('users', 'monthly_episodes_used')
    op.drop_column('users', 'credits')
    op.drop_column('users', 'tier')
