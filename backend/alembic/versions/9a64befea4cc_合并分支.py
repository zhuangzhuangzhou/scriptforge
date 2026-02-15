"""合并分支

Revision ID: 9a64befea4cc
Revises: add_api_log_body, add_llm_status_idx, add_mc_id_to_bd
Create Date: 2026-02-15 16:09:03.638374

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9a64befea4cc'
down_revision: Union[str, None] = ('add_api_log_body', 'add_llm_status_idx', 'add_mc_id_to_bd')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
