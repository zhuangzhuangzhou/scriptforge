"""添加兑换码表

Revision ID: 20260226_add_redeem_codes
Revises: 5420f22114d0_add_announcements_tables
Create Date: 2026-02-26
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260226_add_redeem_codes'
down_revision = '5420f22114d0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 创建兑换码表
    op.create_table(
        'redeem_codes',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('code', sa.String(32), unique=True, nullable=False, index=True),
        sa.Column('type', sa.String(20), nullable=False, default='credits'),
        sa.Column('credits', sa.Integer(), default=0),
        sa.Column('tier', sa.String(20), nullable=True),
        sa.Column('tier_days', sa.Integer(), default=30),
        sa.Column('max_uses', sa.Integer(), default=1),
        sa.Column('used_count', sa.Integer(), default=0),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('expires_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('note', sa.String(500), nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # 创建兑换记录表
    op.create_table(
        'redeem_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('redeem_code_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('redeem_codes.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('code', sa.String(32), nullable=False),
        sa.Column('type', sa.String(20), nullable=False),
        sa.Column('credits_granted', sa.Integer(), default=0),
        sa.Column('tier_before', sa.String(20), nullable=True),
        sa.Column('tier_after', sa.String(20), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table('redeem_records')
    op.drop_table('redeem_codes')
