"""添加 request_body 和 response_body 到 api_logs

Revision ID: add_api_log_body_fields_v2
Revises: 6646e9d6eb5e
Create Date: 2026-02-24

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = 'add_api_log_body_fields_v2'
down_revision = '6646e9d6eb5e'
branch_labels = None
depends_on = None


def upgrade():
    # 添加 request_body 字段
    op.add_column('api_logs', sa.Column('request_body', sa.Text(), nullable=True))
    # 添加 response_body 字段
    op.add_column('api_logs', sa.Column('response_body', sa.Text(), nullable=True))


def downgrade():
    # 删除字段
    op.drop_column('api_logs', 'response_body')
    op.drop_column('api_logs', 'request_body')
