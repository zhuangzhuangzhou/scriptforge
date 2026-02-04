"""add billing tables for subscriptions and billing records

Revision ID: add_billing_tables
Revises: add_user_tier_system
Create Date: 2026-02-04

新增计费系统表，支持：
- 账单记录：记录所有计费事件（充值、消费、退款等）
- 订阅管理：管理用户订阅状态和过期时间
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from datetime import datetime

revision = 'add_billing_tables'
down_revision = 'add_user_tier_system'
branch_labels = None
depends_on = None


def upgrade():
    # 账单记录表
    op.create_table(
        'billing_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),

        # 交易类型：charge(消费), refund(退款), topup(充值), subscription(订阅), adjustment(调整)
        sa.Column('type', sa.String(50), nullable=False),

        # 金额（单位：分）
        sa.Column('amount', sa.Integer, default=0),

        # 积分变化
        sa.Column('credits', sa.Integer, default=0),

        # 交易后余额
        sa.Column('balance_after', sa.Integer, nullable=False),

        # 描述
        sa.Column('description', sa.String(500)),

        # 关联ID（订单号、退款单号等）
        sa.Column('reference_id', sa.String(100)),

        # 时间戳
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), default=datetime.utcnow),
    )

    # 创建索引
    op.create_index('idx_billing_records_user_id', 'billing_records', ['user_id'])
    op.create_index('idx_billing_records_type', 'billing_records', ['type'])
    op.create_index('idx_billing_records_created_at', 'billing_records', ['created_at'])

    # 订阅表
    op.create_table(
        'subscriptions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),

        # 订阅等级：free, creator, studio, enterprise
        sa.Column('tier', sa.String(20), nullable=False),

        # 订阅状态：active(活跃), expired(已过期), cancelled(已取消), suspended(已暂停)
        sa.Column('status', sa.String(20), default='active'),

        # 订阅金额（单位：分）
        sa.Column('amount', sa.Integer, nullable=False),

        # 订阅开始时间
        sa.Column('started_at', sa.TIMESTAMP(timezone=True), nullable=False),

        # 订阅过期时间
        sa.Column('expires_at', sa.TIMESTAMP(timezone=True), nullable=False),

        # 创建时间
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), default=datetime.utcnow),
    )

    # 创建索引
    op.create_index('idx_subscriptions_user_id', 'subscriptions', ['user_id'])
    op.create_index('idx_subscriptions_status', 'subscriptions', ['status'])


def downgrade():
    # 删除索引和表
    op.drop_index('idx_subscriptions_status', table_name='subscriptions')
    op.drop_index('idx_subscriptions_user_id', table_name='subscriptions')
    op.drop_table('subscriptions')

    op.drop_index('idx_billing_records_created_at', table_name='billing_records')
    op.drop_index('idx_billing_records_type', table_name='billing_records')
    op.drop_index('idx_billing_records_user_id', table_name='billing_records')
    op.drop_table('billing_records')
