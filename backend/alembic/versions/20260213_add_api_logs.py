"""add api_logs table

Revision ID: 20260213_add_api_logs
Revises: 20260212_system_config
Create Date: 2026-02-13

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260213_add_api_logs'
down_revision = '20260212_system_config'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'api_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('method', sa.String(10), nullable=False),
        sa.Column('path', sa.String(500), nullable=False),
        sa.Column('query_params', sa.Text(), nullable=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('user_ip', sa.String(50), nullable=True),
        sa.Column('user_agent', sa.String(500), nullable=True),
        sa.Column('status_code', sa.Integer(), nullable=False),
        sa.Column('response_time', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=True),
    )

    # 创建索引
    op.create_index('ix_api_logs_created_at', 'api_logs', ['created_at'])
    op.create_index('ix_api_logs_path', 'api_logs', ['path'])
    op.create_index('ix_api_logs_user_id', 'api_logs', ['user_id'])
    op.create_index('ix_api_logs_status_code', 'api_logs', ['status_code'])


def downgrade() -> None:
    op.drop_index('ix_api_logs_status_code', table_name='api_logs')
    op.drop_index('ix_api_logs_user_id', table_name='api_logs')
    op.drop_index('ix_api_logs_path', table_name='api_logs')
    op.drop_index('ix_api_logs_created_at', table_name='api_logs')
    op.drop_table('api_logs')
