"""合并 feedbacks 和 scripted_chapters 迁移

Revision ID: 20260227_merge_heads
Revises: 20260226_add_feedbacks, 20260226_add_scripted_chapters
Create Date: 2026-02-27
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260227_merge_heads'
down_revision: Union[str, Sequence[str], None] = ('20260226_add_feedbacks', '20260226_add_scripted_chapters')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
