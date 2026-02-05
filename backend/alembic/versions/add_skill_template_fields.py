"""add skill template fields

Revision ID: add_skill_template_fields
Revises: add_skill_visibility
Create Date: 2026-02-04

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_skill_template_fields'
down_revision = 'add_billing_tables'
branch_labels = None
depends_on = None


def upgrade():
    # 为skills表添加模板相关字段
    op.add_column('skills', sa.Column('is_template_based', sa.Boolean(), default=False))
    op.add_column('skills', sa.Column('prompt_template', sa.Text()))
    op.add_column('skills', sa.Column('output_schema', postgresql.JSON()))
    op.add_column('skills', sa.Column('input_variables', postgresql.JSON()))


def downgrade():
    # 删除skills表的模板字段
    op.drop_column('skills', 'input_variables')
    op.drop_column('skills', 'output_schema')
    op.drop_column('skills', 'prompt_template')
    op.drop_column('skills', 'is_template_based')
