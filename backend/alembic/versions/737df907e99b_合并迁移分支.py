"""合并迁移分支

Revision ID: 737df907e99b
Revises: 268402db6fea, add_ai_task_state_machine
Create Date: 2026-02-06 11:06:52.339787

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '737df907e99b'
down_revision: Union[str, None] = ('268402db6fea', 'add_ai_task_state_machine')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
