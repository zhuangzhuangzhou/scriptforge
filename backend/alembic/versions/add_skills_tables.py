"""add skills tables

Revision ID: add_skills_tables
Revises:
Create Date: 2026-02-03

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_skills_tables'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # 创建skills表
    op.create_table(
        'skills',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False, unique=True, index=True),
        sa.Column('display_name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('category', sa.String(50)),
        sa.Column('module_path', sa.String(500), nullable=False),
        sa.Column('class_name', sa.String(100), nullable=False),
        sa.Column('parameters', postgresql.JSON),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('is_builtin', sa.Boolean, default=False),
        sa.Column('version', sa.String(20), default='1.0.0'),
        sa.Column('author', sa.String(100)),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now())
    )

    # 创建user_skill_configs表
    op.create_table(
        'user_skill_configs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('projects.id', ondelete='CASCADE')),
        sa.Column('skill_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('skills.id', ondelete='CASCADE'), nullable=False),
        sa.Column('custom_parameters', postgresql.JSON),
        sa.Column('execution_order', sa.String(10)),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now())
    )


def downgrade():
    op.drop_table('user_skill_configs')
    op.drop_table('skills')
