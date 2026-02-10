"""add model ids to project

Revision ID: add_model_ids_to_project
Revises: 
Create Date: 2026-02-10

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_model_ids_to_project'
down_revision = ('add_ai_task_state_machine', 'ecc01e4bf4bc')  # 合并两个分支
branch_labels = None
depends_on = None


def upgrade():
    # 添加剧情拆解模型 ID
    op.add_column('projects', sa.Column('breakdown_model_id', postgresql.UUID(as_uuid=True), nullable=True))
    
    # 添加剧本生成模型 ID
    op.add_column('projects', sa.Column('script_model_id', postgresql.UUID(as_uuid=True), nullable=True))
    
    # 添加外键约束
    op.create_foreign_key(
        'fk_projects_breakdown_model',
        'projects', 'ai_models',
        ['breakdown_model_id'], ['id'],
        ondelete='SET NULL'
    )
    
    op.create_foreign_key(
        'fk_projects_script_model',
        'projects', 'ai_models',
        ['script_model_id'], ['id'],
        ondelete='SET NULL'
    )


def downgrade():
    # 删除外键约束
    op.drop_constraint('fk_projects_script_model', 'projects', type_='foreignkey')
    op.drop_constraint('fk_projects_breakdown_model', 'projects', type_='foreignkey')
    
    # 删除列
    op.drop_column('projects', 'script_model_id')
    op.drop_column('projects', 'breakdown_model_id')
