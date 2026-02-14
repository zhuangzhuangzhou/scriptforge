"""add task_id and model_config_id to plot_breakdowns

Revision ID: 20260215_analytics
Revises: 20260213_add_llm_call_logs
Create Date: 2026-02-15

为 PlotBreakdown 表添加数据分析所需的关联字段：
- task_id: 关联的 AITask
- model_config_id: 使用的模型配置
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260215_analytics'
down_revision = '20260213_add_llm_call_logs'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 添加 task_id 字段
    op.add_column(
        'plot_breakdowns',
        sa.Column('task_id', postgresql.UUID(as_uuid=True), nullable=True)
    )
    op.create_foreign_key(
        'fk_plot_breakdowns_task_id',
        'plot_breakdowns', 'ai_tasks',
        ['task_id'], ['id'],
        ondelete='SET NULL'
    )
    op.create_index('ix_plot_breakdowns_task_id', 'plot_breakdowns', ['task_id'])

    # 添加 model_config_id 字段
    op.add_column(
        'plot_breakdowns',
        sa.Column('model_config_id', postgresql.UUID(as_uuid=True), nullable=True)
    )
    op.create_foreign_key(
        'fk_plot_breakdowns_model_config_id',
        'plot_breakdowns', 'model_configs',
        ['model_config_id'], ['id'],
        ondelete='SET NULL'
    )
    op.create_index('ix_plot_breakdowns_model_config_id', 'plot_breakdowns', ['model_config_id'])


def downgrade() -> None:
    # 删除 model_config_id
    op.drop_index('ix_plot_breakdowns_model_config_id', table_name='plot_breakdowns')
    op.drop_constraint('fk_plot_breakdowns_model_config_id', 'plot_breakdowns', type_='foreignkey')
    op.drop_column('plot_breakdowns', 'model_config_id')

    # 删除 task_id
    op.drop_index('ix_plot_breakdowns_task_id', table_name='plot_breakdowns')
    op.drop_constraint('fk_plot_breakdowns_task_id', 'plot_breakdowns', type_='foreignkey')
    op.drop_column('plot_breakdowns', 'task_id')
