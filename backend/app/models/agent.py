from sqlalchemy import Column, String, Boolean, JSON, Text, DateTime, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime, timezone
import uuid
from app.core.database import Base


class AgentDefinition(Base):
    """Agent 定义 - 可配置的智能体"""
    __tablename__ = "agent_definitions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False)  # 创建者

    # ============ 基本信息 ============
    name = Column(String(100), nullable=False)           # 内部标识
    display_name = Column(String(255), nullable=False)    # 显示名称
    description = Column(Text)                            # 描述
    category = Column(String(50))                        # 分类

    # ============ Agent 角色配置 ============
    role = Column(Text, nullable=False)                  # 角色设定
    goal = Column(Text, nullable=False)                  # 目标描述
    system_prompt = Column(Text)                         # 系统提示词

    # ============ Workflow 配置 ============
    workflow_config = Column(JSON)                       # 工作流配置
    """
    {
        "steps": [
            {
                "id": "step_1",
                "name": "类型确定",
                "action": "call_skill",          # call_skill | call_agent | conditional
                "target": "webtoon-skill",
                "input_mapping": {"data": "{{input}}"},
                "output_mapping": {"result": "output"},
                "description": "调用 webtoon-skill 确定小说类型"
            },
            {
                "id": "step_2",
                "name": "剧情拆解",
                "action": "conditional",
                "condition": {
                    "type": "command",           # command | state | keyword
                    "value": "/breakdown"
                },
                "then": ["step_2_1", "step_2_2"],
                "else": []
            },
            {
                "id": "step_2_1",
                "name": "执行拆解",
                "action": "call_skill",
                "target": "webtoon-skill",
                "auto_trigger": {
                    "after": "step_2",
                    "condition": "always"
                }
            },
            {
                "id": "step_2_2",
                "name": "质量检查",
                "action": "call_agent",
                "target": "breakdown-aligner",
                "auto_trigger": {
                    "after": "step_2_1",
                    "condition": "always"
                }
            }
        ],
        "entry_point": "detect_state"                   # detect_state | specific_step
    }
    """

    # ============ 触发规则配置 ============
    trigger_rules = Column(JSON)                         # 触发规则
    """
    [
        {
            "id": "rule_1",
            "name": "拆解完成后自动质检",
            "event": "step_completed",                  # step_completed | command_received | state_changed
            "condition": {
                "step_id": "webtoon_breakdown",
                "output_status": "completed"
            },
            "actions": [
                {"type": "call_agent", "target": "breakdown-aligner"}
            ],
            "priority": 1
        },
        {
            "id": "rule_2",
            "name": "剧本创作后自动质检",
            "event": "step_completed",
            "condition": {
                "step_id": "webtoon_script",
                "output_status": "completed"
            },
            "actions": [
                {"type": "call_agent", "target": "webtoon-aligner"}
            ],
            "priority": 1
        },
        {
            "id": "rule_3",
            "name": "关键词触发",
            "event": "command_received",
            "condition": {
                "keywords": ["推翻", "改设定", "改人设", "重排时间线"]
            },
            "actions": [
                {"type": "call_agent", "target": "webtoon-aligner"}
            ],
            "priority": 2
        }
    ]
    """

    # ============ Prompt 模板 ============
    prompt_template = Column(Text, default="{{input}}")   # Prompt 模板

    # ============ 参数配置 ============
    parameters_schema = Column(JSON)                      # 参数 Schema
    default_parameters = Column(JSON)                    # 默认参数

    # ============ 执行配置 ============
    output_format = Column(String(50), default='text')   # text, json, structured

    # ============ 状态 ============
    is_active = Column(Boolean, default=True)
    is_public = Column(Boolean, default=False)           # 是否公开
    usage_count = Column(Integer, default=0)             # 使用次数

    # ============ 元数据 ============
    is_template = Column(Boolean, default=False)          # 是否为模板
    template_source = Column(String(100))                 # 模板来源（built-in, user）
    version = Column(Integer, default=1)                  # 版本号

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class AgentExecution(Base):
    """Agent 执行记录"""
    __tablename__ = "agent_executions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agent_definitions.id", ondelete="CASCADE"))

    # 执行上下文
    pipeline_id = Column(UUID(as_uuid=True))            # 关联的 Pipeline
    node_id = Column(String(100))                       # 触发的节点ID
    step_id = Column(String(100))                        # 当前步骤ID

    # 数据
    input_data = Column(JSON)                           # 输入数据
    output_data = Column(JSON)                          # 输出数据
    context_data = Column(JSON)                         # 上下文数据
    context_history = Column(JSON)                      # 上下文历史

    # 执行状态
    status = Column(String(50), default="pending")      # pending, running, completed, failed
    error_message = Column(Text)
    error_details = Column(JSON)                         # 错误详情

    # 元数据
    execution_time = Column(Integer)                    # 执行时间(ms)
    tokens_used = Column(Integer, default=0)            # 消耗的 tokens
    model_used = Column(String(100))                   # 使用的模型

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class PipelineNodeAgent(Base):
    """Pipeline 节点与 Agent 的绑定"""
    __tablename__ = "pipeline_node_agents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pipeline_id = Column(UUID(as_uuid=True), ForeignKey("pipelines.id", ondelete="CASCADE"))
    node_id = Column(String(100), nullable=False)       # Pipeline 节点 ID

    # 绑定的 Agent
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agent_definitions.id", ondelete="CASCADE"))
    agent_order = Column(Integer, default=0)             # 执行顺序

    # 输入输出映射
    input_mapping = Column(JSON)                        # 输入映射
    output_mapping = Column(JSON)                        # 输出映射

    # 触发条件
    trigger_condition = Column(JSON)                      # 触发条件
    is_optional = Column(Boolean, default=True)         # 是否可选

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class AgentWorkflowExecution(Base):
    """Agent 工作流执行状态"""
    __tablename__ = "agent_workflow_executions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agent_definitions.id", ondelete="CASCADE"))
    execution_id = Column(UUID(as_uuid=True), ForeignKey("agent_executions.id", ondelete="CASCADE"))

    # 工作流状态
    current_step_id = Column(String(100))               # 当前步骤ID
    step_status = Column(JSON)                          # 各步骤状态
    completed_steps = Column(JSON)                      # 已完成步骤

    # 条件分支状态
    branch_taken = Column(JSON)                         # 选择的分支
    conditional_results = Column(JSON)                   # 条件判断结果

    # 自动触发队列
    pending_triggers = Column(JSON)                      # 待触发的动作

    # 质检结果
    quality_checks = Column(JSON)                        # 质检结果队列

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class SimpleAgent(Base):
    """简化的 Agent 模型 - 用于简化工作流系统

    与 AgentDefinition 的区别：
    - 更简单的工作流定义（只支持顺序执行 Skills）
    - 不支持复杂的条件分支和触发规则
    - 专注于 Skill 编排，而非复杂的智能体行为
    """
    __tablename__ = "simple_agents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), unique=True, nullable=False, index=True)
    display_name = Column(String(255), nullable=False)
    description = Column(Text)
    category = Column(String(50))  # breakdown, qa, script

    # 工作流定义（简化版）
    workflow = Column(JSON, nullable=False)
    """
    工作流结构示例：
    {
        "steps": [
            {
                "id": "step1",
                "skill": "conflict_extraction",
                "inputs": {
                    "chapters_text": "${context.chapters_text}"
                },
                "output_key": "conflicts",
                "on_fail": "stop",  # stop, skip, retry
                "max_retries": 0
            },
            {
                "id": "step2",
                "skill": "episode_planning",
                "inputs": {
                    "conflicts": "${step1.conflicts}",
                    "chapters_text": "${context.chapters_text}"
                },
                "output_key": "episodes"
            }
        ]
    }
    """

    # 状态
    is_active = Column(Boolean, default=True)
    is_builtin = Column(Boolean, default=False)

    # 权限控制
    visibility = Column(String(20), default='public')  # public, private
    owner_id = Column(UUID(as_uuid=True), nullable=False)

    # 元数据
    version = Column(String(20), default="1.0.0")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<SimpleAgent {self.name}>"
