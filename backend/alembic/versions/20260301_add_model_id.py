"""add ai_model_id to llm_call_logs

Revision ID: 20260301_add_model_id
Revises: add_api_log_body, add_mc_id_to_bd, add_llm_status_idx, 20260226_add_scripted_chapters, 20260226_prompt_cfg, add_api_log_body_fields_v2, add_skill_template_fields, add_model_ids_to_project
Create Date: 2026-03-01
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20260301_add_model_id'
down_revision: Union[str, Sequence[str], None] = (
    'add_api_log_body',
    'add_mc_id_to_bd',
    'add_llm_status_idx',
    '20260226_add_scripted_chapters',
    '20260226_prompt_cfg',
    'add_api_log_body_fields_v2',
    'add_skill_template_fields',
    'add_model_ids_to_project',
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 添加 ai_model_id 列到 llm_call_logs 表
    op.add_column(
        'llm_call_logs',
        sa.Column(
            'ai_model_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('ai_models.id', ondelete='SET NULL'),
            nullable=True
        )
    )
    # 创建索引
    op.create_index(
        'ix_llm_call_logs_ai_model_id',
        'llm_call_logs',
        ['ai_model_id']
    )


def downgrade() -> None:
    op.drop_index('ix_llm_call_logs_ai_model_id', table_name='llm_call_logs')
    op.drop_column('llm_call_logs', 'ai_model_id')
