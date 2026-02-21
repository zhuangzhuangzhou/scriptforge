"""add_updated_at_to_ai_tasks

Revision ID: d4da2e01cfa5
Revises: cf9391aab2d5
Create Date: 2026-02-20 22:13:15.313171

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4da2e01cfa5'
down_revision: Union[str, None] = 'cf9391aab2d5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 添加 updated_at 字段到 ai_tasks 表
    op.add_column('ai_tasks', sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=True))


def downgrade() -> None:
    # 删除 updated_at 字段
    op.drop_column('ai_tasks', 'updated_at')
