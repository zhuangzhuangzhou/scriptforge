"""添加 status 索引到 llm_call_logs 表

Revision ID: add_llm_call_logs_status_index
Revises: 20260215_skill_system_prompt
Create Date: 2026-02-15

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = 'add_llm_status_idx'
down_revision = '20260215_skill_system_prompt'
branch_labels = None
depends_on = None


def upgrade():
    # 为 status 字段添加索引，优化查询速度
    op.create_index('ix_llm_call_logs_status', 'llm_call_logs', ['status'])


def downgrade():
    op.drop_index('ix_llm_call_logs_status', 'llm_call_logs')
