"""drop prompt from llm_call_logs

Revision ID: cf9391aab2d5
Revises: add_split_rules_table
Create Date: 2026-02-19 19:01:26.085811

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cf9391aab2d5'
down_revision: Union[str, None] = 'add_split_rules_table'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 只删除 prompt 列
    op.drop_column('llm_call_logs', 'prompt')


def downgrade() -> None:
    # 恢复 prompt 列
    op.add_column('llm_call_logs', sa.Column('prompt', sa.TEXT(), nullable=False, server_default=''))
