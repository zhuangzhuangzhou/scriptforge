"""添加用户提示词配置表

Revision ID: 20260226_prompt_cfg
Revises: 20260226_add_feedbacks
Create Date: 2026-02-26

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260226_prompt_cfg'
down_revision = '20260226_add_feedbacks'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'user_prompt_configs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('conflict_prompt_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('character_prompt_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('scene_prompt_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('emotion_prompt_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('plot_hook_prompt_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ),
        sa.ForeignKeyConstraint(['conflict_prompt_id'], ['ai_resources.id'], ),
        sa.ForeignKeyConstraint(['character_prompt_id'], ['ai_resources.id'], ),
        sa.ForeignKeyConstraint(['scene_prompt_id'], ['ai_resources.id'], ),
        sa.ForeignKeyConstraint(['emotion_prompt_id'], ['ai_resources.id'], ),
        sa.ForeignKeyConstraint(['plot_hook_prompt_id'], ['ai_resources.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'project_id', name='uq_user_project_prompt_config')
    )
    op.create_index('ix_user_prompt_configs_user_id', 'user_prompt_configs', ['user_id'])
    op.create_index('ix_user_prompt_configs_project_id', 'user_prompt_configs', ['project_id'])


def downgrade() -> None:
    op.drop_index('ix_user_prompt_configs_project_id', table_name='user_prompt_configs')
    op.drop_index('ix_user_prompt_configs_user_id', table_name='user_prompt_configs')
    op.drop_table('user_prompt_configs')
