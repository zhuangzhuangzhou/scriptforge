"""添加用户反馈表

Revision ID: 20260226_add_feedbacks
Revises: 20260226_add_redeem_codes
Create Date: 2026-02-26
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '20260226_add_feedbacks'
down_revision = '20260226_add_redeem_codes'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'feedbacks',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('type', sa.String(20), nullable=False, default='other', index=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('contact', sa.String(255), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, default='pending', index=True),
        sa.Column('admin_note', sa.Text(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('idx_feedback_user_created', 'feedbacks', ['user_id', 'created_at'])


def downgrade() -> None:
    op.drop_index('idx_feedback_user_created', table_name='feedbacks')
    op.drop_table('feedbacks')
