"""扩展 Skill 模型支持简化执行引擎

Revision ID: 20260211_extend_skill
Revises: eece6c8e3bad
Create Date: 2026-02-11 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20260211_extend_skill'
down_revision: Union[str, None] = 'eece6c8e3bad'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 添加新字段
    op.add_column('skills', sa.Column('input_schema', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('skills', sa.Column('model_config', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('skills', sa.Column('example_input', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('skills', sa.Column('example_output', postgresql.JSONB(astext_type=sa.Text()), nullable=True))

    # 删除旧的 input_variables 字段（如果存在）
    # op.drop_column('skills', 'input_variables')


def downgrade() -> None:
    # 回滚操作
    op.drop_column('skills', 'example_output')
    op.drop_column('skills', 'example_input')
    op.drop_column('skills', 'model_config')
    op.drop_column('skills', 'input_schema')

    # 恢复 input_variables 字段
    # op.add_column('skills', sa.Column('input_variables', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
