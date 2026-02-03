"""add agent system tables (enhanced with workflow config)

Revision ID: add_agent_system
Revises: add_skill_visibility
Create Date: 2026-02-03

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from datetime import datetime

# revision identifiers, used by Alembic.
revision = 'add_agent_system'
down_revision = 'add_skill_visibility'
branch_labels = None
depends_on = None


def upgrade():
    # Agent 定义表（增强版 - 支持 workflow_config 和 trigger_rules）
    op.create_table(
        'agent_definitions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),

        # 基本信息
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('display_name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('category', sa.String(50)),

        # Agent 角色配置
        sa.Column('role', sa.Text, nullable=False),
        sa.Column('goal', sa.Text, nullable=False),
        sa.Column('system_prompt', sa.Text),

        # Workflow 配置
        sa.Column('workflow_config', postgresql.JSON),
        sa.Column('trigger_rules', postgresql.JSON),

        # Prompt 和参数
        sa.Column('prompt_template', sa.Text, default="{{input}}"),
        sa.Column('parameters_schema', postgresql.JSON),
        sa.Column('default_parameters', postgresql.JSON),

        # 执行配置
        sa.Column('output_format', sa.String(50), default='text'),

        # 状态
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('is_public', sa.Boolean, default=False),
        sa.Column('is_template', sa.Boolean, default=False),
        sa.Column('template_source', sa.String(100)),
        sa.Column('usage_count', sa.Integer, default=0),
        sa.Column('version', sa.Integer, default=1),

        sa.Column('created_at', sa.DateTime, default=datetime.utcnow),
        sa.Column('updated_at', sa.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow),
    )

    # 创建索引
    op.create_index('idx_agent_definitions_user_id', 'agent_definitions', ['user_id'])
    op.create_index('idx_agent_definitions_name', 'agent_definitions', ['name'])
    op.create_index('idx_agent_definitions_category', 'agent_definitions', ['category'])

    # Agent 执行记录表（增强版）
    op.create_table(
        'agent_executions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('agent_id', postgresql.UUID(as_uuid=True), nullable=False),

        # 执行上下文
        sa.Column('pipeline_id', postgresql.UUID(as_uuid=True)),
        sa.Column('node_id', sa.String(100)),
        sa.Column('step_id', sa.String(100)),

        # 数据
        sa.Column('input_data', postgresql.JSON),
        sa.Column('output_data', postgresql.JSON),
        sa.Column('context_data', postgresql.JSON),
        sa.Column('context_history', postgresql.JSON),

        # 执行状态
        sa.Column('status', sa.String(50), default='pending'),
        sa.Column('error_message', sa.Text),
        sa.Column('error_details', postgresql.JSON),

        # 元数据
        sa.Column('execution_time', sa.Integer),
        sa.Column('tokens_used', sa.Integer, default=0),
        sa.Column('model_used', sa.String(100)),

        sa.Column('created_at', sa.DateTime, default=datetime.utcnow),
        sa.Column('updated_at', sa.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow),
    )

    op.create_index('idx_agent_executions_agent_id', 'agent_executions', ['agent_id'])
    op.create_index('idx_agent_executions_pipeline_id', 'agent_executions', ['pipeline_id'])
    op.create_index('idx_agent_executions_created_at', 'agent_executions', ['created_at'])

    # Pipeline 节点绑定表
    op.create_table(
        'pipeline_node_agents',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('pipeline_id', postgresql.UUID(as_uuid=True)),
        sa.Column('node_id', sa.String(100), nullable=False),
        sa.Column('agent_id', postgresql.UUID(as_uuid=True)),
        sa.Column('agent_order', sa.Integer, default=0),
        sa.Column('input_mapping', postgresql.JSON),
        sa.Column('output_mapping', postgresql.JSON),
        sa.Column('trigger_condition', postgresql.JSON),
        sa.Column('is_optional', sa.Boolean, default=True),
        sa.Column('created_at', sa.DateTime, default=datetime.utcnow),
    )

    op.create_index('idx_pipeline_node_agents_pipeline', 'pipeline_node_agents', ['pipeline_id', 'node_id'])

    # Agent 工作流执行状态表
    op.create_table(
        'agent_workflow_executions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('agent_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('execution_id', postgresql.UUID(as_uuid=True)),

        # 工作流状态
        sa.Column('current_step_id', sa.String(100)),
        sa.Column('step_status', postgresql.JSON),
        sa.Column('completed_steps', postgresql.JSON),

        # 条件分支状态
        sa.Column('branch_taken', postgresql.JSON),
        sa.Column('conditional_results', postgresql.JSON),

        # 自动触发队列
        sa.Column('pending_triggers', postgresql.JSON),

        # 质检结果
        sa.Column('quality_checks', postgresql.JSON),

        sa.Column('created_at', sa.DateTime, default=datetime.utcnow),
        sa.Column('updated_at', sa.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow),
    )

    op.create_index('idx_workflow_agent_id', 'agent_workflow_executions', ['agent_id'])
    op.create_index('idx_workflow_execution_id', 'agent_workflow_executions', ['execution_id'])


def downgrade():
    # 删除索引和表
    op.drop_table('agent_workflow_executions')
    op.drop_table('pipeline_node_agents')
    op.drop_table('agent_executions')
    op.drop_table('agent_definitions')
