"""简化的 Skill 和 Agent 执行引擎

核心理念：
- Skill = Prompt 模板 + 输入/输出定义
- 执行 = 模板填充 + 模型调用 + JSON 解析
- 不需要复杂的类继承和异步处理
"""
import json
import re
import logging
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class SimpleSkillExecutor:
    """简化的 Skill 执行器

    负责执行单个 Skill：
    1. 从数据库加载 Skill 配置
    2. 填充 Prompt 模板
    3. 调用模型生成
    4. 解析 JSON 响应
    """

    def __init__(self, db: Session, model_adapter, log_publisher=None):
        """初始化执行器

        Args:
            db: 数据库会话
            model_adapter: 模型适配器
            log_publisher: Redis 日志发布器（可选）
        """
        self.db = db
        self.model_adapter = model_adapter
        self.log_publisher = log_publisher

    def execute_skill(
        self,
        skill_name: str,
        inputs: Dict[str, Any],
        task_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """执行单个 Skill

        Args:
            skill_name: Skill 名称
            inputs: 输入数据
            task_id: 任务 ID（用于日志推送）

        Returns:
            执行结果

        Raises:
            ValueError: Skill 不存在或输入参数错误
        """
        from app.models.skill import Skill

        # 1. 从数据库加载 Skill 配置
        skill = self.db.query(Skill).filter(
            Skill.name == skill_name,
            Skill.is_active == True
        ).first()

        if not skill:
            raise ValueError(f"Skill '{skill_name}' 不存在或未激活")

        # 2. 检查是否为模板驱动的 Skill
        if not skill.is_template_based:
            raise ValueError(f"Skill '{skill_name}' 不是模板驱动的 Skill，请使用传统方式执行")

        # 3. 填充 Prompt 模板
        try:
            prompt = skill.prompt_template.format(**inputs)
        except KeyError as e:
            raise ValueError(f"缺少必需的输入参数: {e}")

        # 4. 发布步骤开始
        if self.log_publisher and task_id:
            self.log_publisher.publish_step_start(
                task_id,
                skill.display_name or skill.name
            )

        # 5. 调用模型
        model_config = skill.model_config or {}
        temperature = model_config.get("temperature", 0.7)
        max_tokens = model_config.get("max_tokens", 2000)

        try:
            # 使用流式生成
            full_response = ""
            for chunk in self.model_adapter.stream_generate(
                prompt,
                temperature=temperature,
                max_tokens=max_tokens
            ):
                if self.log_publisher and task_id:
                    self.log_publisher.publish_stream_chunk(
                        task_id,
                        skill.display_name or skill.name,
                        chunk
                    )
                full_response += chunk

            # 6. 解析 JSON 响应
            result = self._parse_json(full_response)

            # 7. 发布步骤结束
            if self.log_publisher and task_id:
                self.log_publisher.publish_step_end(
                    task_id,
                    skill.display_name or skill.name,
                    {"status": "success"}
                )

            return result

        except Exception as e:
            # 发布错误
            if self.log_publisher and task_id:
                self.log_publisher.publish_error(
                    task_id,
                    f"执行失败: {str(e)}",
                    error_code="SKILL_EXECUTION_ERROR",
                    step_name=skill.display_name or skill.name
                )
            raise

    def _parse_json(self, response: str) -> Any:
        """解析 JSON 响应

        Args:
            response: AI 模型的响应文本

        Returns:
            解析后的 JSON 对象

        Raises:
            ValueError: 无法解析 JSON
        """
        # 尝试直接解析
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass

        # 提取 JSON 代码块
        json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # 提取任何 JSON 数组或对象
        json_match = re.search(r'(\[.*\]|\{.*\})', response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass

        # 解析失败
        raise ValueError(f"无法解析 JSON 响应: {response[:200]}...")


class SimpleAgentExecutor:
    """简化的 Agent 执行器

    负责执行 Agent 工作流：
    1. 加载 Agent 配置
    2. 按顺序执行 Skill
    3. 传递变量和结果
    4. 处理错误和重试
    """

    def __init__(self, db: Session, model_adapter, log_publisher=None):
        """初始化执行器

        Args:
            db: 数据库会话
            model_adapter: 模型适配器
            log_publisher: Redis 日志发布器（可选）
        """
        self.db = db
        self.skill_executor = SimpleSkillExecutor(db, model_adapter, log_publisher)
        self.log_publisher = log_publisher

    def execute_agent(
        self,
        agent_name: str,
        context: Dict[str, Any],
        task_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """执行 Agent 工作流

        Args:
            agent_name: Agent 名称
            context: 初始上下文数据
            task_id: 任务 ID（用于日志推送）

        Returns:
            执行结果，包含所有步骤的输出

        Raises:
            ValueError: Agent 不存在或配置错误
        """
        from app.models.agent import Agent

        # 1. 加载 Agent 配置
        agent = self.db.query(Agent).filter(
            Agent.name == agent_name,
            Agent.is_active == True
        ).first()

        if not agent:
            raise ValueError(f"Agent '{agent_name}' 不存在或未激活")

        # 2. 执行工作流
        workflow = agent.workflow
        if not workflow or "steps" not in workflow:
            raise ValueError(f"Agent '{agent_name}' 的工作流配置无效")

        steps = workflow.get("steps", [])
        results = {"context": context}

        for step in steps:
            step_id = step.get("id")
            skill_name = step.get("skill")
            input_template = step.get("inputs", {})
            output_key = step.get("output_key", step_id)
            on_fail = step.get("on_fail", "stop")
            max_retries = step.get("max_retries", 0)

            if not skill_name:
                logger.warning(f"步骤 {step_id} 缺少 skill 字段，跳过")
                continue

            # 解析输入（支持变量引用）
            try:
                inputs = self._resolve_inputs(input_template, results)
            except Exception as e:
                logger.error(f"解析输入失败: {e}")
                if on_fail == "stop":
                    raise
                continue

            # 执行 Skill（支持重试）
            retry_count = 0
            while retry_count <= max_retries:
                try:
                    result = self.skill_executor.execute_skill(
                        skill_name=skill_name,
                        inputs=inputs,
                        task_id=task_id
                    )

                    # 保存结果
                    results[output_key] = result
                    results[step_id] = result
                    break  # 成功，跳出重试循环

                except Exception as e:
                    retry_count += 1
                    logger.error(f"执行 Skill '{skill_name}' 失败 (尝试 {retry_count}/{max_retries + 1}): {e}")

                    if retry_count > max_retries:
                        # 超过最大重试次数
                        if on_fail == "stop":
                            raise
                        elif on_fail == "skip":
                            logger.warning(f"跳过步骤 {step_id}")
                            break
                        elif on_fail == "retry":
                            # 已经重试过了，还是失败
                            raise
                    else:
                        # 继续重试
                        if self.log_publisher and task_id:
                            self.log_publisher.publish_warning(
                                task_id,
                                f"重试执行 {skill_name} (第 {retry_count} 次)"
                            )

        return results

    def _resolve_inputs(
        self,
        input_template: Dict[str, Any],
        results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """解析输入模板中的变量引用

        支持：
        - ${context.chapters_text} - 引用初始上下文
        - ${step1.conflicts} - 引用步骤结果
        - ${conflicts} - 引用结果中的顶级键

        Args:
            input_template: 输入模板
            results: 当前结果集

        Returns:
            解析后的输入数据

        Raises:
            ValueError: 变量不存在
        """
        def resolve_value(value):
            if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                # 变量引用
                path = value[2:-1]  # 去掉 ${ 和 }
                parts = path.split(".")

                current = results
                for part in parts:
                    if isinstance(current, dict):
                        current = current.get(part)
                    else:
                        raise ValueError(f"变量 '{path}' 的路径无效")

                    if current is None:
                        raise ValueError(f"变量 '{path}' 不存在")

                return current
            elif isinstance(value, dict):
                return {k: resolve_value(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [resolve_value(v) for v in value]
            else:
                return value

        return {k: resolve_value(v) for k, v in input_template.items()}
