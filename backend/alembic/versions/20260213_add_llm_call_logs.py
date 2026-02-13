"""add llm_call_logs table

Revision ID: 20260213_add_llm_call_logs
Revises: 20260213_add_api_logs
Create Date: 2026-02-13

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260213_add_llm_call_logs'
down_revision = '20260213_add_api_logs'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'llm_call_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('task_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('ai_tasks.id', ondelete='SET NULL'), nullable=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('projects.id', ondelete='SET NULL'), nullable=True),
        sa.Column('provider', sa.String(50), nullable=False),
        sa.Column('model_name', sa.String(100), nullable=False),
        sa.Column('skill_name', sa.String(100), nullable=True),
        sa.Column('stage', sa.String(100), nullable=True),
        sa.Column('prompt', sa.Text(), nullable=False),
        sa.Column('prompt_tokens', sa.Integer(), nullable=True),
        sa.Column('temperature', sa.Float(), nullable=True),
        sa.Column('max_tokens', sa.Integer(), nullable=True),
        sa.Column('response', sa.Text(), nullable=True),
        sa.Column('response_tokens', sa.Integer(), nullable=True),
        sa.Column('total_tokens', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='success'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('latency_ms', sa.Integer(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=True),
    )

    # 创建索引
    op.create_index('ix_llm_call_logs_created_at', 'llm_call_logs', ['created_at'])
    op.create_index('ix_llm_call_logs_task_id', 'llm_call_logs', ['task_id'])
    op.create_index('ix_llm_call_logs_user_id', 'llm_call_logs', ['user_id'])
    op.create_index('ix_llm_call_logs_provider', 'llm_call_logs', ['provider'])
    op.create_index('ix_llm_call_logs_model_name', 'llm_call_logs', ['model_name'])
    op.create_index('ix_llm_call_logs_skill_name', 'llm_call_logs', ['skill_name'])


def downgrade() -> None:
    op.drop_index('ix_llm_call_logs_skill_name', table_name='llm_call_logs')
    op.drop_index('ix_llm_call_logs_model_name', table_name='llm_call_logs')
    op.drop_index('ix_llm_call_logs_provider', table_name='llm_call_logs')
    op.drop_index('ix_llm_call_logs_user_id', table_name='llm_call_logs')
    op.drop_index('ix_llm_call_logs_task_id', table_name='llm_call_logs')
    op.drop_index('ix_llm_call_logs_created_at', table_name='llm_call_logs')
    op.drop_table('llm_call_logs')
