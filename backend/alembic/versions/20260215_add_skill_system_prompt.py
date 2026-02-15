"""Add system_prompt to skills table

Revision ID: 20260215_skill_system_prompt
Revises: fix_plot_breakdowns_model_fk
Create Date: 2026-02-15
"""
from alembic import op
import sqlalchemy as sa

revision = '20260215_skill_system_prompt'
down_revision = 'fix_plot_breakdowns_model_fk'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('skills', sa.Column('system_prompt', sa.Text(), nullable=True))


def downgrade():
    op.drop_column('skills', 'system_prompt')
