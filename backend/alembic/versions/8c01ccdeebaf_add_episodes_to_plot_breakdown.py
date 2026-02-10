"""add_episodes_to_plot_breakdown

Revision ID: 8c01ccdeebaf
Revises: add_model_ids_to_project
Create Date: 2026-02-10 18:33:31.340798

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8c01ccdeebaf'
down_revision: Union[str, None] = 'add_model_ids_to_project'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 添加 episodes 字段到 plot_breakdowns 表
    op.add_column('plot_breakdowns', sa.Column('episodes', sa.dialects.postgresql.JSONB(), nullable=True))


def downgrade() -> None:
    # 删除 episodes 字段
    op.drop_column('plot_breakdowns', 'episodes')
