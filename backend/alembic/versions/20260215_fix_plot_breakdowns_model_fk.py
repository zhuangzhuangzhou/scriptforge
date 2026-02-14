"""新增 ai_model_id 字段到 plot_breakdowns 表

保留原有的 model_config_id 字段，新增 ai_model_id 字段指向 ai_models 表

Revision ID: fix_plot_breakdowns_model_fk
Revises: 20260215_analytics
Create Date: 2026-02-15
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = 'fix_plot_breakdowns_model_fk'
down_revision = '20260215_analytics'
branch_labels = None
depends_on = None


def upgrade():
    # 新增 ai_model_id 字段
    op.add_column('plot_breakdowns', sa.Column('ai_model_id', UUID(as_uuid=True), nullable=True))
    op.create_index('ix_plot_breakdowns_ai_model_id', 'plot_breakdowns', ['ai_model_id'])
    op.create_foreign_key(
        'fk_plot_breakdowns_ai_model_id',
        'plot_breakdowns',
        'ai_models',
        ['ai_model_id'],
        ['id'],
        ondelete='SET NULL'
    )


def downgrade():
    op.drop_constraint('fk_plot_breakdowns_ai_model_id', 'plot_breakdowns', type_='foreignkey')
    op.drop_index('ix_plot_breakdowns_ai_model_id', 'plot_breakdowns')
    op.drop_column('plot_breakdowns', 'ai_model_id')
