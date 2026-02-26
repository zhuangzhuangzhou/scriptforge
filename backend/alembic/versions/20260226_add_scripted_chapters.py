"""添加 scripted_chapters 字段到 projects 表

Revision ID: 20260226_add_scripted_chapters
Revises: 20260226_add_redeem_codes
Create Date: 2026-02-26
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20260226_add_scripted_chapters'
down_revision = '20260226_add_redeem_codes'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('projects', sa.Column('scripted_chapters', sa.Integer(), nullable=True, server_default='0'))


def downgrade() -> None:
    op.drop_column('projects', 'scripted_chapters')
