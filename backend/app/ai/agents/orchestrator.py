"""
Agent 调度器 - 支持工作流执行、条件触发和自动质检

功能：
1. 工作流执行 - 按配置顺序执行步骤
2. 条件触发 - 根据条件判断执行分支
3. 自动质检 - 完成特定步骤后自动触发质检
4. 上下文管理 - 维护执行上下文
"""

import re
import json
import time
from typing import Any, Dict, List, Optional, Callable, TYPE_CHECKING
from enum import Enum
from pydantic import BaseModel
from app.ai.adapters.base import BaseAdapter
from app.ai.skills.skill_loader import SkillLoader

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class StepAction(str, Enum):
    """步骤动作类型"""
    CALL_SKILL = "call_skill"
    CALL_AGENT = "call_agent"
    CONDITIONAL = "conditional"
    BRANCH = "branch"


class EventType(str, Enum):
    """事件类型"""
    STEP_COMPLETED = "step_completed"
    COMMAND_RECEIVED = "command_received"
    STATE_CHANGED = "state_changed"
    QUALITY_CHECK_PASSED = "quality_check_passed"
    QUALITY_CHECK_FAILED = "quality_check_failed"


class TriggerCondition(BaseModel):
    """触发条件"""
    type: str  # command, state, keyword, always
    value: Optional[Any] = None


class WorkflowStep(BaseModel):
    """工作流步骤"""
    id: str
    name: str
    action: str  # call_skill, call_agent, conditional, branch
    target: Optional[str] = None  # 目标 Skill/Agent 名称
    input_mapping: Optional[Dict[str, str]] = None
    output_mapping: Optional[Dict[str, str]] = None
    condition: Optional[TriggerCondition] = None
    then: Optional[List[str]] = None  # 条件为真时执行的步骤
    else_steps: Optional[List[str]] = None  # 条件为假时执行的步骤
    auto_trigger: Optional[Dict[str, Any]] = None  # 自动触发配置
    description: Optional[str] = None


class TriggerRule(BaseModel):
    """触发规则"""
    id: str
    name: str
    event: str  # step_completed, command_received, state_changed
    condition: Optional[Dict[str, Any]] = None
    actions: List[Dict[str, Any]]
    priority: int = 0


class ExecutionContext(BaseModel):
    """执行上下文"""
    input_data: Any
    context_data: Dict[str, Any] = {}
    history: List[Dict[str, Any]] = []
    current_step: Optional[str] = None
    quality_checks: List[Dict[str, Any]] = []


class AgentOrchestrator:
    """
    Agent 调度器

    使用示例：
    ```python
    orchestrator = AgentOrchestrator(model_adapter)

    # 配置 Agent
    agent_config = {
        "name": "网文改编编剧",
        "role": "你是一名经验丰富的网文改编编剧...",
        "goal": "将网络小说改编为漫剧",
        "workflow_config": {
            "steps": [
                {
                    "id": "detect_state",
                    "name": "状态检测",
                    "action": "conditional",
                    "condition": {"type": "command", "value": "/breakdown"},
                    "then": ["breakdown_1", "breakdown_2"]
                },
                {
                    "id": "breakdown_1",
                    "name": "执行拆解",
                    "action": "call_skill",
                    "target": "webtoon-skill"
                },
                {
                    "id": "breakdown_2",
                    "name": "质量检查",
                    "action": "call_agent",
                    "target": "breakdown-aligner",
                    "auto_trigger": {"after": "breakdown_1", "condition": "always"}
                }
            ],
            "entry_point": "detect_state"
        },
        "trigger_rules": [
            {
                "id": "auto_quality_check",
                "name": "拆解后自动质检",
                "event": "step_completed",
                "condition": {"step_id": "breakdown_1", "status": "completed"},
                "actions": [{"type": "call_agent", "target": "breakdown-aligner"}]
            }
        ]
    }

    # 执行
    result = await orchestrator.run(
        agent_config=agent_config,
        input_data={"novel": "...", "chapter": 6},
        user_command="/breakdown"
    )
    ```
    """

    def __init__(
        self,
        model_adapter: BaseAdapter,
        db_session: Optional["AsyncSession"] = None
    ):
        self.model_adapter = model_adapter
        self.db_session = db_session
        self.step_executors: Dict[str, Callable] = {}
        self.skill_loader = SkillLoader()

    async def run(
        self,
        agent_config: Dict[str, Any],
        input_data: Any,
        user_command: Optional[str] = None,
        context_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        执行 Agent 工作流

        Args:
            agent_config: Agent 配置
            input_data: 输入数据
            user_command: 用户命令（如 /breakdown, /script）
            context_data: 上下文数据

        Returns:
            执行结果
        """
        start_time = time.time()

        # 初始化上下文
        context = ExecutionContext(
            input_data=input_data,
            context_data=context_data or {},
            history=[]
        )

        # 解析配置
        workflow_config = agent_config.get("workflow_config", {})
        trigger_rules = agent_config.get("trigger_rules", [])

        steps = {s["id"]: WorkflowStep(**s) for s in workflow_config.get("steps", [])}
        rules = [TriggerRule(**r) for r in trigger_rules]

        # 确定入口点
        entry_point = workflow_config.get("entry_point", "detect_state")

        # 执行工作流
        result = await self._execute_workflow(
            steps=steps,
            entry_point=entry_point,
            context=context,
            user_command=user_command,
            trigger_rules=rules,
            agent_config=agent_config
        )

        execution_time = int((time.time() - start_time) * 1000)

        return {
            "success": result.get("success", False),
            "output": result.get("output"),
            "context": context.context_data,
            "history": context.history,
            "quality_checks": context.quality_checks,
            "execution_time": execution_time
        }

    async def _execute_workflow(
        self,
        steps: Dict[str, WorkflowStep],
        entry_point: str,
        context: ExecutionContext,
        user_command: Optional[str],
        trigger_rules: List[TriggerRule],
        agent_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """执行工作流"""
        # 要执行的步骤队列
        step_queue = [entry_point]
        executed_steps = set()

        while step_queue:
            step_id = step_queue.pop(0)

            if step_id in executed_steps:
                continue

            step = steps.get(step_id)
            if not step:
                continue

            context.current_step = step_id
            step_result = None

            try:
                # 根据动作类型执行
                if step.action == StepAction.CALL_SKILL.value:
                    step_result = await self._execute_skill(
                        step=step,
                        context=context,
                        agent_config=agent_config
                    )
                elif step.action == StepAction.CALL_AGENT.value:
                    step_result = await self._execute_agent(
                        step=step,
                        context=context,
                        agent_config=agent_config
                    )
                elif step.action == StepAction.CONDITIONAL.value:
                    step_queue.extend(
                        await self._execute_conditional(
                            step=step,
                            context=context,
                            user_command=user_command,
                            steps=steps
                        )
                    )
                    executed_steps.add(step_id)
                    continue
                else:
                    step_result = {"success": True, "output": step.description}

                # 记录历史
                context.history.append({
                    "step_id": step_id,
                    "step_name": step.name,
                    "result": step_result,
                    "timestamp": time.time()
                })

                executed_steps.add(step_id)

                # 处理输出映射
                if step.output_mapping and step_result:
                    for key, value in step.output_mapping.items():
                        if isinstance(step_result.get("output"), dict):
                            context.context_data[key] = step_result["output"].get(value)

                # 检查是否触发自动质检
                if step.auto_trigger:
                    trigger_queue = await self._check_auto_trigger(
                        step=step,
                        step_result=step_result,
                        context=context,
                        agent_config=agent_config
                    )
                    step_queue.extend(trigger_queue)

                # 检查触发规则
                triggered = await self._check_trigger_rules(
                    step_id=step_id,
                    step_result=step_result,
                    context=context,
                    user_command=user_command,
                    rules=trigger_rules,
                    steps=steps,
                    agent_config=agent_config
                )

                # 添加触发的步骤到队列
                for action in triggered:
                    if action["type"] == "step":
                        step_queue.append(action["target"])
                    elif action["type"] == "call_agent":
                        # 创建临时的 agent 调用步骤
                        await self._execute_agent(
                            step=WorkflowStep(
                                id=f"trigger_{int(time.time())}",
                                name=action.get("name", "质检"),
                                action="call_agent",
                                target=action["target"]
                            ),
                            context=context,
                            agent_config=agent_config
                        )

            except Exception as e:
                context.history.append({
                    "step_id": step_id,
                    "step_name": step.name,
                    "error": str(e),
                    "timestamp": time.time()
                })
                return {"success": False, "error": str(e)}

        return {"success": True, "output": context.context_data}

    async def _execute_skill(
        self,
        step: WorkflowStep,
        context: ExecutionContext,
        agent_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """执行 Skill 调用"""
        skill_name = step.target
        if not skill_name:
            return {"success": False, "error": "No skill target specified"}

        # 应用输入映射
        input_data = self._apply_mapping(
            context.input_data,
            step.input_mapping
        )

        # 尝试从 SkillLoader 加载 Skill 实例
        skill_instance = self.skill_loader.get_skill(skill_name)

        if skill_instance:
            # 使用已注册的 Skill
            result = await skill_instance.execute(input_data)
            return {"success": True, "output": result}

        # 回退：使用通用 prompt 执行
        prompt = self._build_prompt(
            agent_config=agent_config,
            step=step,
            input_data=input_data
        )

        response = await self.model_adapter.generate(
            prompt=prompt,
            system_prompt=agent_config.get("system_prompt", ""),
            temperature=0.7
        )

        return {"success": True, "output": response}

    async def _execute_agent(
        self,
        step: WorkflowStep,
        context: ExecutionContext,
        agent_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """执行 Sub-Agent 调用"""
        target_name = step.target
        if not target_name:
            return {"success": False, "error": "No agent target specified"}

        # 从数据库加载 Sub-Agent 配置
        sub_agent_config = await self._load_agent_config(target_name)

        if not sub_agent_config:
            # 回退：使用简单的 prompt 执行
            prompt = self._build_prompt(
                agent_config=agent_config,
                step=step,
                input_data=context.context_data
            )

            response = await self.model_adapter.generate(
                prompt=prompt,
                system_prompt=f"你是 {target_name}，负责 {step.name}",
                temperature=0.7
            )

            return {
                "success": True,
                "output": {
                    "status": "PASS",
                    "message": response if isinstance(response, str) else response.get("content", ""),
                    "agent": target_name
                }
            }

        # 递归调用 orchestrator 执行 Sub-Agent
        sub_orchestrator = AgentOrchestrator(
            model_adapter=self.model_adapter,
            db_session=self.db_session
        )

        result = await sub_orchestrator.run(
            agent_config=sub_agent_config,
            input_data=context.context_data,
            context_data=context.context_data
        )

        return result

    async def _load_agent_config(self, agent_name: str) -> Optional[Dict[str, Any]]:
        """从数据库加载 Agent 配置"""
        if not self.db_session:
            return None

        from sqlalchemy import select
        from app.models.agent import AgentDefinition

        stmt = select(AgentDefinition).where(
            AgentDefinition.name == agent_name,
            AgentDefinition.is_active == True
        )

        result = await self.db_session.execute(stmt)
        agent_def = result.scalar_one_or_none()

        if not agent_def:
            return None

        return {
            "id": str(agent_def.id),
            "name": agent_def.name,
            "display_name": agent_def.display_name,
            "role": agent_def.role,
            "goal": agent_def.goal,
            "system_prompt": agent_def.system_prompt,
            "prompt_template": agent_def.prompt_template,
            "workflow_config": agent_def.workflow_config or {},
            "trigger_rules": agent_def.trigger_rules or [],
            "output_format": agent_def.output_format
        }

    async def _execute_conditional(
        self,
        step: WorkflowStep,
        context: ExecutionContext,
        user_command: Optional[str],
        steps: Dict[str, WorkflowStep]
    ) -> List[str]:
        """执行条件判断"""
        condition = step.condition

        if not condition:
            return step.then or []

        should_execute = False

        if condition.type == "command":
            # 根据命令判断
            should_execute = user_command == condition.value
        elif condition.type == "keyword":
            # 根据关键词判断
            if user_command:
                should_execute = any(
                    kw in user_command
                    for kw in (condition.value or [])
                )
        elif condition.type == "state":
            # 根据状态判断
            should_execute = context.context_data.get(condition.value) is True
        elif condition.type == "always":
            should_execute = True

        # 记录条件判断结果
        context.context_data.setdefault("conditional_results", {})[step.id] = {
            "condition": condition.dict(),
            "result": should_execute
        }

        if should_execute:
            return step.then or []
        else:
            return step.else_steps or []

    async def _check_auto_trigger(
        self,
        step: WorkflowStep,
        step_result: Dict[str, Any],
        context: ExecutionContext,
        agent_config: Dict[str, Any]
    ) -> List[str]:
        """检查是否满足自动触发条件"""
        auto_trigger = step.auto_trigger
        if not auto_trigger:
            return []

        after_step = auto_trigger.get("after")
        condition = auto_trigger.get("condition", "always")

        # 检查前置步骤是否完成
        if after_step and after_step != step.id:
            completed = any(h["step_id"] == after_step for h in context.history)
            if not completed:
                return []

        # 检查条件
        if condition == "always":
            # 检查是否已完成
            has_completed = any(
                h["step_id"] == step.id and h.get("result", {}).get("success")
                for h in context.history
            )
            if has_completed:
                return []
        elif condition == "quality_passed":
            if not step_result.get("quality_passed", False):
                return []

        # 返回触发的步骤
        return auto_trigger.get("trigger_steps", [])

    async def _check_trigger_rules(
        self,
        step_id: str,
        step_result: Dict[str, Any],
        context: ExecutionContext,
        user_command: Optional[str],
        rules: List[TriggerRule],
        steps: Dict[str, WorkflowStep],
        agent_config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """检查触发规则"""
        triggered = []

        for rule in sorted(rules, key=lambda r: r.priority, reverse=True):
            should_trigger = False

            if rule.event == "step_completed":
                # 检查步骤完成
                if rule.condition:
                    step_condition = rule.condition.get("step_id")
                    if step_condition == step_id:
                        should_trigger = True

            elif rule.event == "command_received":
                # 检查命令
                if user_command and rule.condition:
                    keywords = rule.condition.get("keywords", [])
                    if any(kw in user_command for kw in keywords):
                        should_trigger = True

            if should_trigger:
                triggered.extend(rule.actions)

                # 记录质检结果
                context.quality_checks.append({
                    "rule_id": rule.id,
                    "rule_name": rule.name,
                    "triggered": True,
                    "actions": rule.actions
                })

        return triggered

    def _apply_mapping(
        self,
        data: Any,
        mapping: Optional[Dict[str, str]]
    ) -> Any:
        """应用输入/输出映射"""
        if not mapping or not data:
            return data

        if isinstance(data, dict):
            result = {}
            for output_key, input_path in mapping.items():
                # 支持嵌套路径，如 "result.data"
                parts = input_path.split(".")
                current = data
                for part in parts:
                    if isinstance(current, dict):
                        current = current.get(part)
                    else:
                        current = None
                        break
                result[output_key] = current
            return result if result else data

        return data

    def _build_prompt(
        self,
        agent_config: Dict[str, Any],
        step: WorkflowStep,
        input_data: Any
    ) -> str:
        """构建 Prompt"""
        template = step.description or agent_config.get("prompt_template", "{{input}}")

        # 准备变量
        variables = {
            "input": str(input_data) if not isinstance(input_data, str) else input_data,
            "role": agent_config.get("role", ""),
            "goal": agent_config.get("goal", ""),
            "step_name": step.name,
            "step_description": step.description or ""
        }

        # 替换变量
        prompt = template
        for key, value in variables.items():
            prompt = prompt.replace(f"{{{{ {key} }}}}", str(value))
            prompt = prompt.replace(f"{{{{{key}}}}}", str(value))

        return prompt


class SkillExecutor:
    """Skill 执行器 - 包装 AgentExecutor 用于调用 Skills"""

    def __init__(self, model_adapter: BaseAdapter):
        self.model_adapter = model_adapter
        self.skill_loader = SkillLoader()

    async def execute(
        self,
        skill_name: str,
        input_data: Any,
        parameters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        执行 Skill

        Args:
            skill_name: Skill 名称
            input_data: 输入数据
            parameters: 参数

        Returns:
            Skill 执行结果
        """
        # 从 SkillLoader 加载 Skill 实例
        skill_instance = self.skill_loader.get_skill(skill_name)

        if skill_instance:
            if parameters:
                skill_instance.set_parameters(parameters)
            result = await skill_instance.execute(input_data)
            return {
                "success": True,
                "skill": skill_name,
                "output": result
            }

        return {
            "success": False,
            "skill": skill_name,
            "error": f"Skill {skill_name} not found"
        }


class SubAgentExecutor:
    """Sub-Agent 执行器 - 用于调用其他 Agent"""

    def __init__(
        self,
        model_adapter: BaseAdapter,
        db_session: Optional["AsyncSession"] = None
    ):
        self.model_adapter = model_adapter
        self.db_session = db_session
        self.orchestrator = AgentOrchestrator(model_adapter, db_session)

    async def execute(
        self,
        agent_id: str,
        input_data: Any,
        user_command: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        执行 Sub-Agent

        Args:
            agent_id: Agent ID 或名称
            input_data: 输入数据
            user_command: 用户命令

        Returns:
            Agent 执行结果
        """
        # 从数据库加载 Agent 配置
        agent_config = await self._load_agent_config(agent_id)

        if not agent_config:
            return {
                "success": False,
                "agent": agent_id,
                "error": f"Agent {agent_id} not found"
            }

        # 使用 orchestrator 执行
        result = await self.orchestrator.run(
            agent_config=agent_config,
            input_data=input_data,
            user_command=user_command
        )

        return {
            "success": result.get("success", False),
            "agent": agent_id,
            "output": result.get("output")
        }

    async def _load_agent_config(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """从数据库加载 Agent 配置"""
        if not self.db_session:
            return None

        from sqlalchemy import select
        from app.models.agent import AgentDefinition
        import uuid

        # 尝试按 ID 或名称查找
        try:
            agent_uuid = uuid.UUID(agent_id)
            stmt = select(AgentDefinition).where(
                AgentDefinition.id == agent_uuid,
                AgentDefinition.is_active == True
            )
        except ValueError:
            # 不是有效的 UUID，按名称查找
            stmt = select(AgentDefinition).where(
                AgentDefinition.name == agent_id,
                AgentDefinition.is_active == True
            )

        result = await self.db_session.execute(stmt)
        agent_def = result.scalar_one_or_none()

        if not agent_def:
            return None

        return {
            "id": str(agent_def.id),
            "name": agent_def.name,
            "display_name": agent_def.display_name,
            "role": agent_def.role,
            "goal": agent_def.goal,
            "system_prompt": agent_def.system_prompt,
            "prompt_template": agent_def.prompt_template,
            "workflow_config": agent_def.workflow_config or {},
            "trigger_rules": agent_def.trigger_rules or [],
            "output_format": agent_def.output_format
        }
