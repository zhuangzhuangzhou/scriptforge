"""简化的 Skill 和 Agent 执行引擎

核心理念：
- Skill = Prompt 模板 + 输入/输出定义
- 执行 = 模板填充 + 模型调用 + JSON 解析
- Agent = 工作流编排 + 循环控制 + 条件执行
"""
import json
from app.core.status import TaskStatus
import re
import logging
from typing import Dict, Any, Optional, List, Union
from sqlalchemy.orm import Session
from app.models.ai_task import AITask
from app.models.project import Project
from app.core.exceptions import TaskCancelledError
from app.ai.llm_logger import llm_context

logger = logging.getLogger(__name__)


def _try_fix_incomplete_json(json_str: str) -> str:
    """尝试修复不完整的 JSON 字符串

    常见问题：
    - 缺少结尾的 } 或 ]
    - 字符串未闭合
    - 尾部有多余字符

    Args:
        json_str: 可能不完整的 JSON 字符串

    Returns:
        修复后的 JSON 字符串
    """
    # 移除尾部的 ``` 标记
    json_str = re.sub(r'`+\s*$', '', json_str)

    # 统计括号
    open_braces = json_str.count('{')
    close_braces = json_str.count('}')
    open_brackets = json_str.count('[')
    close_brackets = json_str.count(']')

    # 补充缺失的闭合括号
    if open_braces > close_braces:
        # 检查是否在字符串中间被截断（查找未闭合的引号）
        # 简单处理：如果最后一个字符不是 } 或 ]，尝试截断到最后一个完整的值
        last_valid_pos = max(
            json_str.rfind('},'),
            json_str.rfind('}]'),
            json_str.rfind('"}'),
            json_str.rfind('"]'),
            json_str.rfind('" }'),
            json_str.rfind('" ]'),
        )
        if last_valid_pos > 0:
            # 截断到最后一个完整的位置
            json_str = json_str[:last_valid_pos + 1]
            # 重新统计
            open_braces = json_str.count('{')
            close_braces = json_str.count('}')
            open_brackets = json_str.count('[')
            close_brackets = json_str.count(']')

        # 补充缺失的 }
        json_str += '}' * (open_braces - close_braces)

    if open_brackets > close_brackets:
        json_str += ']' * (open_brackets - close_brackets)

    return json_str


def parse_llm_response(
    response: str,
    default: Any = None,
    logger_obj=None,
    raise_on_empty: bool = False
) -> Any:
    """解析 LLM 响应文本为 JSON（高度容错版本）

    这是统一的 JSON 解析函数，建议在整个项目中优先使用。

    解析策略（按优先级）：
    1. 直接解析整个响应
    2. 提取 ```json ... ``` 代码块
    3. 提取 ``` ... ```（无语言标记）
    4. 提取 { ... } JSON 对象
    5. 提取 [ ... ] JSON 数组
    6. 尝试修复不完整的 JSON
    7. 如果以上都失败，返回默认值

    Args:
        response: LLM 响应文本
        default: 解析失败时返回的默认值（默认为空列表）
        logger_obj: 日志对象，如果提供则记录错误
        raise_on_empty: 是否在空响应时抛出异常

    Returns:
        解析后的 JSON 对象，或默认值

    Raises:
        ValueError: 当 raise_on_empty=True 且响应为空时
    """
    if default is None:
        default = []

    # 检查响应是否为空
    if not response or not isinstance(response, str):
        if raise_on_empty:
            raise ValueError("LLM 返回空响应")
        return default

    response = response.strip()
    if not response:
        if raise_on_empty:
            raise ValueError("LLM 返回空字符串")
        return default

    # 策略1：直接解析
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        pass

    # 策略2：提取 ```json ... ``` 代码块
    json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
    if json_match:
        json_str = json_match.group(1).strip()
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            json_str = _try_fix_incomplete_json(json_str)
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                pass

    # 策略3：提取 ``` ... ```（无语言标记）
    json_match = re.search(r'```\s*(.*?)\s*```', response, re.DOTALL)
    if json_match:
        json_str = json_match.group(1).strip()
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            json_str = _try_fix_incomplete_json(json_str)
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                pass

    # 策略4：提取 { ... } 或 [ ... ]
    json_match = re.search(r'(\{[\s\S]*\}|\[[\s\S]*\])', response)
    if json_match:
        json_str = json_match.group(1).strip()
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            json_str = _try_fix_incomplete_json(json_str)
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                pass

    # 策略5：检查是否包含空响应关键词
    if any(keyword in response for keyword in ['没有', '无', '空', 'null', 'None', '[]', '{}']):
        return []

    # 解析失败
    if logger_obj:
        logger_obj.error(
            f"JSON 解析失败，响应内容共 {len(response)} 字符:\n"
            f"--- 开始响应 ---\n{response[:500]}\n"
            f"{'... (截断)' if len(response) > 500 else '--- 结束响应 ---'}"
        )
    return default


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

        # 2. 预处理输入：将非字符串类型转换为 JSON 字符串
        processed_inputs = {}
        for key, value in inputs.items():
            if isinstance(value, str):
                processed_inputs[key] = value
            elif isinstance(value, (list, dict)):
                processed_inputs[key] = json.dumps(value, ensure_ascii=False, indent=2)
            elif value is None:
                processed_inputs[key] = ""
            else:
                processed_inputs[key] = str(value)

        # 3. 填充 Prompt 模板
        try:
            prompt = skill.prompt_template.format(**processed_inputs)
        except KeyError as e:
            raise ValueError(f"缺少必需的输入参数: {e}")

        system_prompt = skill.system_prompt or ""

        # 4. 发布步骤开始（统一显示名称）
        step_display_name = self._normalize_step_name(skill.display_name or skill.name)
        if task_id:
            try:
                from app.core.progress import update_task_progress_sync
                progress_value = None
                if skill.name == "webtoon_breakdown":
                    progress_value = 20
                elif skill.name == "breakdown_aligner":
                    progress_value = 70
                update_task_progress_sync(
                    self.db,
                    task_id,
                    progress=progress_value,
                    current_step=f"{step_display_name}中..."
                )
            except Exception:
                pass

        if self.log_publisher and task_id:
            self.log_publisher.publish_step_start(
                task_id,
                step_display_name
            )

        if task_id and self._is_task_cancelled(task_id):
            raise TaskCancelledError("任务已取消，停止执行")

        # 5. 调用模型
        # 优先级：Skill 配置 > 模型默认配置 > 硬编码默认值
        skill_config = skill.model_config or {}

        # 从 model_adapter 获取模型默认配置
        model_defaults = getattr(self.model_adapter, 'model_config', {}) or {}
        model_max_output = model_defaults.get('max_output_tokens') or model_defaults.get('max_tokens')
        model_temperature = model_defaults.get('temperature_default') or model_defaults.get('temperature')

        # 合并配置：Skill 覆盖 > 模型默认 > 硬编码默认
        temperature = skill_config.get("temperature") or model_temperature or 0.7
        max_tokens = skill_config.get("max_tokens") or model_max_output or 1000000

        # 确保 temperature 是 float 类型
        if hasattr(temperature, '__float__'):
            temperature = float(temperature)

        task_context = self._get_llm_task_context(task_id, skill)

        try:
            # 尝试使用流式生成
            full_response = ""
            stream_failed = False

            # 初始化流式 JSON 解析器（用于实时格式化输出）
            from app.utils.stream_json_parser import StreamJsonParser
            from app.utils.log_formatter import format_json_object, detect_content_type

            json_parser = StreamJsonParser()
            step_display_name = self._normalize_step_name(skill.display_name or skill.name)
            content_type = detect_content_type(step_display_name)
            formatted_index = 0

            try:
                with llm_context(**task_context):
                    for chunk in self.model_adapter.stream_generate(
                        prompt,
                        system_prompt=system_prompt,
                        temperature=temperature,
                        max_tokens=max_tokens
                    ):
                        if task_id and self._is_task_cancelled(task_id):
                            raise TaskCancelledError("任务已取消，停止流式输出")
                        if chunk:  # 确保 chunk 不为 None
                            if self.log_publisher and task_id:
                                # 发送原始 JSON 片段
                                self.log_publisher.publish_stream_chunk(
                                    task_id,
                                    step_display_name,
                                    chunk
                                )

                                # 解析并发送格式化内容
                                parsed_objects = json_parser.feed(chunk)
                                for obj in parsed_objects:
                                    formatted_text = format_json_object(
                                        obj, content_type, formatted_index
                                    )
                                    self.log_publisher.publish_formatted_chunk(
                                        task_id,
                                        step_display_name,
                                        formatted_text + "\n"
                                    )
                                    formatted_index += 1

                            full_response += chunk
            except Exception as stream_error:
                # 流式调用失败，回退到非流式
                logger.warning(f"流式调用失败，回退到非流式: {stream_error}")
                stream_failed = True

            # 如果流式失败或响应为空，使用非流式调用
            if stream_failed or not full_response.strip():
                logger.info("使用非流式调用...")
                if task_id and self._is_task_cancelled(task_id):
                    raise TaskCancelledError("任务已取消，停止非流式调用")
                with llm_context(**task_context):
                    full_response = self.model_adapter.generate(
                        prompt,
                        system_prompt=system_prompt,
                        temperature=temperature,
                        max_tokens=max_tokens
                    )
                # 确保响应是字符串
                if isinstance(full_response, dict) and "content" in full_response:
                    full_response = full_response["content"]

            # 6. 解析 JSON 响应
            result = self._parse_json(full_response)

            # 若流式未产出任何格式化内容，则补发格式化日志，保证 Console 可见
            if formatted_index == 0 and self.log_publisher and task_id:
                try:
                    if full_response:
                        self.log_publisher.publish_stream_chunk(
                            task_id,
                            step_display_name,
                            str(full_response)
                        )

                    items = None
                    if isinstance(result, list):
                        items = result
                    elif isinstance(result, dict) and "plot_points" in result:
                        items = result.get("plot_points") or []
                    elif result is not None:
                        items = [result]

                    if items is not None:
                        formatted_index = 0
                        for obj in items:
                            formatted_text = format_json_object(
                                obj, content_type, formatted_index
                            )
                            self.log_publisher.publish_formatted_chunk(
                                task_id,
                                step_display_name,
                                formatted_text + "\n"
                            )
                            formatted_index += 1
                except Exception:
                    pass

            # 7. 发布步骤结束
            if self.log_publisher and task_id:
                self.log_publisher.publish_step_end(
                    task_id,
                    step_display_name,
                    {"status": "success"}
                )

            return result

        except Exception as e:
            if isinstance(e, TaskCancelledError):
                raise
            # 获取模型信息
            model_info = ""
            if hasattr(self.model_adapter, 'model_name'):
                model_info = f" [模型: {self.model_adapter.model_name}]"
            if hasattr(self.model_adapter, 'provider_name'):
                model_info += f" [提供商: {self.model_adapter.provider_name}]"

            error_msg = f"执行失败: {str(e)}{model_info}"

            # 发布错误
            if self.log_publisher and task_id:
                self.log_publisher.publish_error(
                    task_id,
                    error_msg,
                    error_code="SKILL_EXECUTION_ERROR",
                    step_name=step_display_name
                )
            raise Exception(error_msg) from e

    def _is_task_cancelled(self, task_id: str) -> bool:
        try:
            task = self.db.query(AITask).filter(AITask.id == task_id).first()
            if not task:
                return False
            return task.status in (TaskStatus.CANCELLING, TaskStatus.CANCELED, "cancelled")
        except Exception:
            return False

    def _normalize_step_name(self, name: str) -> str:
        # 规范化 step_name 输出（Console / WS / 进度一致）
        # 规则：
        # - 任何“质量校验/质量检查/质检/剧情拆解质量校验” => “质量检查”
        # - 任何“网文改编剧情拆解/剧情拆解/剧集拆解” => “剧集拆解”
        if not name:
            return name
        if any(key in name for key in ["剧情拆解质量校验", "质量校验", "质量检查", "质检"]):
            return "质量检查"
        if any(key in name for key in ["网文改编剧情拆解", "剧情拆解", "剧集拆解"]):
            return "剧集拆解"
        return name

    def _get_llm_task_context(self, task_id: Optional[str], skill) -> Dict[str, Any]:
        if not task_id:
            return {
                "task_id": None,
                "user_id": None,
                "project_id": None,
                "skill_name": skill.name,
                "stage": skill.display_name or skill.name
            }
        try:
            task = self.db.query(AITask).filter(AITask.id == task_id).first()
            project_id = None
            user_id = None
            if task and task.project_id:
                project_id = str(task.project_id)
                project = self.db.query(Project).filter(Project.id == task.project_id).first()
                if project:
                    user_id = str(project.user_id)
            return {
                "task_id": str(task_id),
                "user_id": user_id,
                "project_id": project_id,
                "skill_name": skill.name,
                "stage": skill.display_name or skill.name
            }
        except Exception:
            return {
                "task_id": str(task_id),
                "user_id": None,
                "project_id": None,
                "skill_name": skill.name,
                "stage": skill.display_name or skill.name
            }

    def _parse_json(self, response: str) -> Any:
        """解析 JSON 响应（使用通用解析函数）

        Args:
            response: AI 模型的响应文本

        Returns:
            解析后的 JSON 对象（列表或字典）

        Raises:
            ValueError: 响应为空或解析失败
        """
        # 使用通用解析函数，自动处理各种边缘情况
        return parse_llm_response(
            response=response,
            default=None,  # 不使用默认值，让函数在失败时抛出异常
            logger_obj=logger,
            raise_on_empty=True  # 空响应时抛出异常
        )


class SimpleAgentExecutor:
    """增强的 Agent 执行器

    支持的工作流类型：
    - sequential（默认）：顺序执行所有步骤
    - loop：循环执行直到满足退出条件

    支持的步骤特性：
    - condition：条件执行（表达式为真时才执行）
    - on_fail：失败处理策略（stop/skip/retry）
    - max_retries：最大重试次数
    - output_key：输出结果的键名
    - transform：结果转换表达式
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
        from app.models.agent import SimpleAgent

        # 1. 加载 Agent 配置
        agent = self.db.query(SimpleAgent).filter(
            SimpleAgent.name == agent_name,
            SimpleAgent.is_active == True
        ).first()

        if not agent:
            raise ValueError(f"Agent '{agent_name}' 不存在或未激活")

        # 2. 解析工作流配置
        workflow = agent.workflow
        if not workflow or "steps" not in workflow:
            raise ValueError(f"Agent '{agent_name}' 的工作流配置无效")

        workflow_type = workflow.get("type", "sequential")

        # 发布 Agent 开始
        if self.log_publisher and task_id:
            self.log_publisher.publish_info(
                task_id,
                f"🤖 启动智能流程：{agent.display_name or agent.name}"
            )

        # 3. 根据工作流类型执行
        if workflow_type == "loop":
            results = self._execute_loop_workflow(workflow, context, task_id)
        else:
            results = self._execute_sequential_workflow(workflow, context, task_id)

        # 发布 Agent 完成
        if self.log_publisher and task_id:
            self.log_publisher.publish_success(
                task_id,
                f"🎉 {agent.display_name or agent.name} 完成"
            )

        return results

    def _execute_sequential_workflow(
        self,
        workflow: Dict[str, Any],
        context: Dict[str, Any],
        task_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """执行顺序工作流

        按顺序执行所有步骤，支持条件执行。

        Args:
            workflow: 工作流配置
            context: 初始上下文
            task_id: 任务 ID

        Returns:
            执行结果
        """
        steps = workflow.get("steps", [])
        results = {"context": context}

        for step in steps:
            step_result = self._execute_step(step, results, task_id)
            if step_result is not None:
                # 合并步骤结果到 results
                results.update(step_result)

        return results

    def _execute_loop_workflow(
        self,
        workflow: Dict[str, Any],
        context: Dict[str, Any],
        task_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """执行循环工作流

        循环执行步骤直到满足退出条件或达到最大迭代次数。

        Args:
            workflow: 工作流配置
            context: 初始上下文
            task_id: 任务 ID

        Returns:
            执行结果
        """
        steps = workflow.get("steps", [])
        max_iterations = workflow.get("max_iterations", 3)
        exit_condition = workflow.get("exit_condition", "false")

        results = {"context": context, "_iteration": 0}

        for iteration in range(max_iterations):
            results["_iteration"] = iteration + 1

            if self.log_publisher and task_id:
                # 发送结构化的轮次信息（供前端标题栏显示）
                self.log_publisher.publish_round_info(
                    task_id,
                    current_round=iteration + 1,
                    total_rounds=max_iterations
                )
                # 同时发送文本日志
                self.log_publisher.publish_info(
                    task_id,
                    f"🔄 第 {iteration + 1} 轮处理（共 {max_iterations} 轮）"
                )

            # 执行所有步骤
            for step in steps:
                step_result = self._execute_step(step, results, task_id)
                if step_result is not None:
                    results.update(step_result)

            # 检查退出条件
            if self._evaluate_condition(exit_condition, results):
                if self.log_publisher and task_id:
                    self.log_publisher.publish_success(
                        task_id,
                        f"✅ 质量检查通过，第 {iteration + 1} 轮完成"
                    )
                break
        else:
            # 达到最大迭代次数
            if self.log_publisher and task_id:
                self.log_publisher.publish_warning(
                    task_id,
                    f"⚠️ 已完成 {max_iterations} 轮处理，结果可能需要人工复核"
                )

        # 清理内部变量
        results.pop("_iteration", None)
        return results

    def _execute_step(
        self,
        step: Dict[str, Any],
        results: Dict[str, Any],
        task_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """执行单个步骤

        支持：
        - 条件执行（condition）
        - Skill 调用（skill）
        - 子 Agent 调用（agent）
        - 失败处理（on_fail）
        - 重试机制（max_retries）
        - 结果转换（transform）

        Args:
            step: 步骤配置
            results: 当前结果集
            task_id: 任务 ID

        Returns:
            步骤执行结果，如果跳过则返回 None
        """
        step_id = step.get("id", "unknown")
        condition = step.get("condition")
        skill_name = step.get("skill")
        agent_name = step.get("agent")
        input_template = step.get("inputs", {})
        output_key = step.get("output_key", step_id)
        on_fail = step.get("on_fail", "stop")
        max_retries = step.get("max_retries", 0)
        transform = step.get("transform")

        # 1. 检查条件
        if condition and not self._evaluate_condition(condition, results):
            logger.info(f"步骤 {step_id} 条件不满足，跳过")
            # 条件不满足时不发布日志，避免用户困惑
            return None

        # 2. 确定执行类型
        if not skill_name and not agent_name:
            logger.warning(f"步骤 {step_id} 缺少 skill 或 agent 字段，跳过")
            return None

        # 3. 解析输入
        try:
            inputs = self._resolve_inputs(input_template, results)
        except Exception as e:
            logger.error(f"步骤 {step_id} 解析输入失败: {e}")
            if on_fail == "stop":
                raise
            return None
        
        if self.log_publisher and task_id and step_id == "breakdown_retry":
            qa_feedback = inputs.get("qa_feedback")
            fb_len = len(qa_feedback) if isinstance(qa_feedback, str) else 0
            self.log_publisher.publish_info(
                task_id,
                f"🧩 修复输入检查: qa_feedback_len={fb_len}"
            )

        # 4. 执行（支持重试）
        retry_count = 0
        last_error = None

        while retry_count <= max_retries:
            try:
                if skill_name:
                    if self.log_publisher and task_id:
                        self.log_publisher.publish_info(
                            task_id,
                            f"▶️ 执行步骤: {step_id} (skill={skill_name})"
                        )
                    # 执行 Skill
                    result = self.skill_executor.execute_skill(
                        skill_name=skill_name,
                        inputs=inputs,
                        task_id=task_id
                    )
                else:
                    if self.log_publisher and task_id:
                        self.log_publisher.publish_info(
                            task_id,
                            f"▶️ 执行步骤: {step_id} (agent={agent_name})"
                        )
                    # 执行子 Agent（递归调用）
                    result = self.execute_agent(
                        agent_name=agent_name,
                        context=inputs,
                        task_id=task_id
                    )

                # 5. 应用结果转换
                if transform:
                    result = self._apply_transform(transform, result, results)

                # 兼容 QA 输出为单元素数组的情况，避免条件评估失败
                if output_key in ("qa_result", "qa") and isinstance(result, list):
                    if len(result) == 1 and isinstance(result[0], dict):
                        result = result[0]
                    elif len(result) == 0:
                        result = {}

                # 6. 返回结果
                return {
                    output_key: result,
                    step_id: result
                }

            except Exception as e:
                retry_count += 1
                last_error = e
                logger.error(
                    f"步骤 {step_id} 执行失败 (尝试 {retry_count}/{max_retries + 1}): {e}"
                )

                if retry_count <= max_retries:
                    # 继续重试
                    if self.log_publisher and task_id:
                        self.log_publisher.publish_warning(
                            task_id,
                            f"🔁 正在重试...（第 {retry_count} 次）"
                        )
                else:
                    # 超过最大重试次数
                    if on_fail == "stop":
                        raise
                    elif on_fail == "skip":
                        logger.warning(f"跳过步骤 {step_id}")
                        if self.log_publisher and task_id:
                            self.log_publisher.publish_warning(
                                task_id,
                                f"⚠️ 部分步骤未完成，继续处理..."
                            )
                        return None

        return None

    def _evaluate_condition(
        self,
        condition: str,
        results: Dict[str, Any]
    ) -> bool:
        """评估条件表达式

        支持的表达式：
        - 简单比较：qa_result.status == 'PASS'
        - 数值比较：qa_result.score >= 70
        - 逻辑运算：status == 'PASS' or score >= 60
        - 存在检查：qa_result.fix_instructions
        - 否定：not qa_result.has_errors

        Args:
            condition: 条件表达式字符串
            results: 当前结果集

        Returns:
            条件是否满足
        """
        if not condition:
            return True

        try:
            # 构建安全的评估环境
            eval_context = self._flatten_results(results)

            # 替换变量引用为实际值
            evaluated_condition = self._substitute_variables(condition, eval_context)

            # 安全评估
            return self._safe_eval(evaluated_condition, eval_context)
        except Exception as e:
            logger.warning(f"条件评估失败 '{condition}': {e}")
            return False

    def _flatten_results(self, results: Dict[str, Any], prefix: str = "") -> Dict[str, Any]:
        """扁平化结果字典，用于条件评估

        将嵌套字典转换为点分隔的键，如：
        {"qa_result": {"status": "PASS"}} -> {"qa_result.status": "PASS", "qa_result": {...}}

        Args:
            results: 结果字典
            prefix: 键前缀

        Returns:
            扁平化后的字典
        """
        flat = {}
        for key, value in results.items():
            full_key = f"{prefix}{key}" if prefix else key
            flat[full_key] = value

            if isinstance(value, dict):
                # 递归扁平化
                nested = self._flatten_results(value, f"{full_key}.")
                flat.update(nested)

        return flat

    def _substitute_variables(self, expression: str, context: Dict[str, Any]) -> str:
        """替换表达式中的变量引用

        Args:
            expression: 表达式字符串
            context: 变量上下文

        Returns:
            替换后的表达式
        """
        # 匹配变量名（支持点分隔）
        var_pattern = r'\b([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*)\b'

        def replace_var(match):
            var_name = match.group(1)
            # 跳过 Python 关键字和布尔值
            if var_name in ('and', 'or', 'not', 'True', 'False', 'None', 'in', 'is'):
                return var_name

            if var_name in context:
                value = context[var_name]
                if isinstance(value, str):
                    return f"'{value}'"
                elif value is None:
                    return 'None'
                elif isinstance(value, bool):
                    return str(value)
                elif isinstance(value, (int, float)):
                    return str(value)
                elif isinstance(value, (list, dict)):
                    return repr(value)
                else:
                    return repr(value)
            return var_name

        return re.sub(var_pattern, replace_var, expression)

    def _safe_eval(self, expression: str, context: Dict[str, Any]) -> bool:
        """安全地评估表达式

        只允许基本的比较和逻辑运算。

        Args:
            expression: 表达式字符串
            context: 变量上下文

        Returns:
            评估结果
        """
        # 允许的操作符和函数
        allowed_names = {
            'True': True,
            'False': False,
            'None': None,
            'len': len,
            'str': str,
            'int': int,
            'float': float,
            'bool': bool,
        }

        # 添加上下文变量
        allowed_names.update(context)

        try:
            # 使用 eval 但限制可用的名称
            result = eval(expression, {"__builtins__": {}}, allowed_names)
            return bool(result)
        except Exception as e:
            logger.warning(f"表达式评估失败 '{expression}': {e}")
            return False

    def _apply_transform(
        self,
        transform: str,
        result: Any,
        results: Dict[str, Any]
    ) -> Any:
        """应用结果转换

        支持简单的属性访问和方法调用。

        Args:
            transform: 转换表达式
            result: 原始结果
            results: 当前结果集

        Returns:
            转换后的结果
        """
        if not transform:
            return result

        try:
            # 构建评估上下文
            context = {
                "result": result,
                "results": results,
                **results
            }

            # 安全评估转换表达式
            return eval(transform, {"__builtins__": {}}, context)
        except Exception as e:
            logger.warning(f"结果转换失败 '{transform}': {e}")
            return result

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
        - ${qa_result.fix_instructions} - 嵌套属性访问

        Args:
            input_template: 输入模板
            results: 当前结果集

        Returns:
            解析后的输入数据

        Raises:
            ValueError: 变量不存在
        """
        def resolve_value(value):
            if isinstance(value, str) and "${" in value and "}" in value:
                # 支持字符串内插（例如："问题列表: ${qa_result.issues}"）
                import json
                import re

                def resolve_path(path: str):
                    parts = path.split(".")
                    current = results
                    for part in parts:
                        if isinstance(current, dict):
                            current = current.get(part)
                        elif hasattr(current, part):
                            current = getattr(current, part)
                        else:
                            raise ValueError(f"变量 '{path}' 的路径无效")
                        if current is None:
                            logger.warning(f"变量 '{path}' 的值为 None")
                            return None
                    return current

                def repl(match):
                    path = match.group(1)
                    current = resolve_path(path)
                    if current is None:
                        return ""
                    if isinstance(current, (dict, list)):
                        return json.dumps(current, ensure_ascii=False)
                    return str(current)

                return re.sub(r"\$\{([^}]+)\}", repl, value)
            elif isinstance(value, dict):
                return {k: resolve_value(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [resolve_value(v) for v in value]
            else:
                return value

        return {k: resolve_value(v) for k, v in input_template.items()}
