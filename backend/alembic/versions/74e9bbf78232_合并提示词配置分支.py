"""合并提示词配置分支

Revision ID: 74e9bbf78232
Revises: 20260226_add_scripted_chapters, 20260226_prompt_cfg
Create Date: 2026-02-26 13:18:28.076054

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '74e9bbf78232'
down_revision: Union[str, None] = ('20260226_add_scripted_chapters', '20260226_prompt_cfg')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
