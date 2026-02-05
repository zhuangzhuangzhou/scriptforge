"""add skill visibility fields

Revision ID: add_skill_visibility
Revises: add_pipeline_tables
Create Date: 2026-02-03

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid

# revision identifiers, used by alembic.
revision = 'add_skill_visibility'
down_revision = 'add_pipeline_tables'
branch_labels = None
depends_on = None


def upgrade():
    # 为skills表添加权限字段（分步处理，避免NOT NULL冲突）
    op.add_column('skills', sa.Column('visibility', sa.String(20), default='public'))
    # 先添加允许NULL的owner_id
    op.add_column('skills', sa.Column('owner_id', postgresql.UUID(as_uuid=True), nullable=True))
    # 更新现有记录的owner_id为系统管理员ID（避免NOT NULL冲突）
    op.execute("UPDATE skills SET owner_id = '00000000-0000-0000-0000-000000000001' WHERE owner_id IS NULL")
    # 修改为NOT NULL
    op.alter_column('skills', 'owner_id', nullable=False)
    op.add_column('skills', sa.Column('allowed_users', postgresql.JSON))

    # 为skill_versions表添加权限字段（同样分步处理）
    op.add_column('skill_versions', sa.Column('visibility', sa.String(20), default='public'))
    op.add_column('skill_versions', sa.Column('owner_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.execute("UPDATE skill_versions SET owner_id = '00000000-0000-0000-0000-000000000001' WHERE owner_id IS NULL")
    op.alter_column('skill_versions', 'owner_id', nullable=False)
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
