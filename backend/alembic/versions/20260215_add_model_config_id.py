"""新增 model_config_id 字段到 plot_breakdowns 表

保留原有的 ai_model_id 字段，新增 model_config_id 字段指向 model_configs 表

Revision ID: add_model_config_id_to_breakdowns
Revises: fix_plot_breakdowns_model_fk
Create Date: 2026-02-15
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = 'add_mc_id_to_bd'
down_revision = 'fix_plot_breakdowns_model_fk'
branch_labels = None
depends_on = None


def upgrade():
    # 检查列是否已存在
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    columns = [c['name'] for c in inspector.get_columns('plot_breakdowns')]
    indexes = [i['name'] for i in inspector.get_indexes('plot_breakdowns')]
    foreign_keys = inspector.get_foreign_keys('plot_breakdowns')

    # 检查外键是否存在
    fk_names = [fk['name'] for fk in foreign_keys]

    if 'model_config_id' not in columns:
        # 新增 model_config_id 字段
        op.add_column('plot_breakdowns', sa.Column('model_config_id', UUID(as_uuid=True), nullable=True))

    if 'ix_plot_breakdowns_model_config_id' not in indexes:
        op.create_index('ix_plot_breakdowns_model_config_id', 'plot_breakdowns', ['model_config_id'])

    if 'fk_plot_breakdowns_model_config_id' not in fk_names:
        op.create_foreign_key(
            'fk_plot_breakdowns_model_config_id',
            'plot_breakdowns',
            'model_configs',
            ['model_config_id'],
            ['id'],
            ondelete='SET NULL'
        )


def downgrade():
    op.drop_constraint('fk_plot_breakdowns_model_config_id', 'plot_breakdowns', type_='foreignkey')
    op.drop_index('ix_plot_breakdowns_model_config_id', 'plot_breakdowns')
    op.drop_column('plot_breakdowns', 'model_config_id')
