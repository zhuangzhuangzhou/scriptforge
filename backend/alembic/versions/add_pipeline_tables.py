"""add pipeline and skill version tables

Revision ID: add_pipeline_tables
Revises:
Create Date: 2026-02-03

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_pipeline_tables'
down_revision = '208695f1899f'
branch_labels = None
depends_on = None


def upgrade():
    # 创建pipelines表
    op.create_table(
        'pipelines',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('config', postgresql.JSON),
        sa.Column('stages_config', postgresql.JSON),
        sa.Column('is_default', sa.Boolean, default=False),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('version', sa.Integer, default=1),
        sa.Column('parent_pipeline_id', postgresql.UUID(as_uuid=True)),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now())
    )

    # 创建pipeline_stages表
    op.create_table(
        'pipeline_stages',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('pipeline_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('pipelines.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('display_name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('skills', postgresql.JSON),
        sa.Column('skills_order', postgresql.JSON),
        sa.Column('config', postgresql.JSON),
        sa.Column('input_mapping', postgresql.JSON),
        sa.Column('output_mapping', postgresql.JSON),
        sa.Column('order', sa.Integer, default=0),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now())
    )

    # 创建pipeline_executions表
    op.create_table(
        'pipeline_executions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('pipeline_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('pipelines.id', ondelete='CASCADE'), nullable=False),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('projects.id', ondelete='CASCADE')),
        sa.Column('status', sa.String(50), default='pending'),
        sa.Column('current_stage', sa.String(100)),
        sa.Column('progress', sa.Integer, default=0),
        sa.Column('current_step', sa.String(100)),
        sa.Column('result', postgresql.JSON),
        sa.Column('error_message', sa.Text),
        sa.Column('celery_task_id', sa.String(255)),
        sa.Column('started_at', sa.DateTime),
        sa.Column('completed_at', sa.DateTime),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now())
    )

    # 创建skill_versions表
    op.create_table(
        'skill_versions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('skill_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('version', sa.String(20), nullable=False),
        sa.Column('version_number', sa.Integer, default=1),
        sa.Column('code', sa.Text, nullable=False),
        sa.Column('parameters_schema', postgresql.JSON),
        sa.Column('description', sa.Text),
        sa.Column('changelog', sa.Text),
        sa.Column('is_published', sa.Boolean, default=False),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('source_version_id', postgresql.UUID(as_uuid=True)),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now())
    )

    # 创建skill_execution_logs表
    op.create_table(
        'skill_execution_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('skill_version_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('execution_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('input_data', postgresql.JSON),
        sa.Column('output_data', postgresql.JSON),
        sa.Column('execution_time', sa.Integer),
        sa.Column('status', sa.String(50), default='pending'),
        sa.Column('error_message', sa.Text),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now())
    )


def downgrade():
    op.drop_table('skill_execution_logs')
    op.drop_table('skill_versions')
    op.drop_table('pipeline_executions')
    op.drop_table('pipeline_stages')
    op.drop_table('pipelines')
