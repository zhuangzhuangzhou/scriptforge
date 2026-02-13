"""添加纯积分制系统字段

Revision ID: 20260212_credits
Revises:
Create Date: 2026-02-12

变更：
- 新增 monthly_credits_granted: 本月已赠送积分
- 新增 credits_reset_at: 积分赠送重置时间
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260212_credits'
down_revision = 'ccda3b05995c'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 添加月度积分赠送字段
    op.add_column('users', sa.Column('monthly_credits_granted', sa.Integer(), nullable=True, server_default='0'))
    op.add_column('users', sa.Column('credits_reset_at', sa.TIMESTAMP(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'credits_reset_at')
    op.drop_column('users', 'monthly_credits_granted')
