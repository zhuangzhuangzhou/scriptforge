"""添加 request_body 和 response_body 到 api_logs

Revision ID: add_api_log_body_fields
Revises: 20260215_skill_system_prompt
Create Date: 2026-02-15

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = 'add_api_log_body'
down_revision = '20260215_skill_system_prompt'
branch_labels = None
depends_on = None


def upgrade():
    # 添加 request_body 字段
    op.add_column('api_logs', sa.Column('request_body', sa.Text(), nullable=True))
    # 添加 response_body 字段
    op.add_column('api_logs', sa.Column('response_body', sa.Text(), nullable=True))


def downgrade():
    # 删除字段
    op.drop_column('api_logs', 'request_body')
    op.drop_column('api_logs', 'response_body')
