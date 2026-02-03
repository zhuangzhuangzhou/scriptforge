"""add skill visibility fields

Revision ID: add_skill_visibility
Revises: add_pipeline_tables
Create Date: 2026-02-03

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_skill_visibility'
down_revision = 'add_pipeline_tables'
branch_labels = None
depends_on = None


def upgrade():
    # 为skills表添加权限字段
    op.add_column('skills', sa.Column('visibility', sa.String(20), default='public'))
    op.add_column('skills', sa.Column('owner_id', postgresql.UUID(as_uuid=True), nullable=False))
    op.add_column('skills', sa.Column('allowed_users', postgresql.JSON))

    # 为skill_versions表添加权限字段
    op.add_column('skill_versions', sa.Column('visibility', sa.String(20), default='public'))
    op.add_column('skill_versions', sa.Column('owner_id', postgresql.UUID(as_uuid=True), nullable=False))
    op.add_column('skill_versions', sa.Column('allowed_users', postgresql.JSON))


def downgrade():
    # 删除skill_versions表的字段
    op.drop_column('skill_versions', 'allowed_users')
    op.drop_column('skill_versions', 'owner_id')
    op.drop_column('skill_versions', 'visibility')

    # 删除skills表的字段
    op.drop_column('skills', 'allowed_users')
    op.drop_column('skills', 'owner_id')
    op.drop_column('skills', 'visibility')
