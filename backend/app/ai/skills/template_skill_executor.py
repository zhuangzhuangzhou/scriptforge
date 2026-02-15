import json
import re
import logging
from typing import Dict, Any, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.skill import Skill
from app.ai.adapters import get_adapter
from app.ai.llm_logger import llm_context

logger = logging.getLogger(__name__)


class TemplateSkillExecutor:
    """模板 Skill 执行器

    用于执行基于模板的用户可编辑 Skill。
    从数据库加载 Skill 定义，替换模板变量，调用 LLM 生成结果。
    """

    def __init__(self, db: AsyncSession, model_adapter=None):
        self.db = db
        self._model_adapter = model_adapter

    async def _get_model_adapter(self, user_id: Optional[str] = None):
        """获取模型适配器（懒加载）

        Args:
            user_id: 用户ID，用于获取用户自定义配置
        """
        if self._model_adapter is None:
            self._model_adapter = await get_adapter(
                user_id=user_id,
                db=self.db
            )
        return self._model_adapter

    async def execute(
        self,
        skill_id: str,
        variables: Dict[str, Any],
        user_id: Optional[str] = None,
        task_id: Optional[str] = None,
        project_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """执行模板 Skill

        Args:
            skill_id: Skill ID
            variables: 模板变量字典
            user_id: 用户 ID（用于权限检查）

        Returns:
            执行结果字典
        """
        # 1. 从数据库加载 Skill
        skill = await self._load_skill(skill_id)

        if not skill:
            raise ValueError(f"Skill 不存在: {skill_id}")

        if not skill.is_template_based:
            raise ValueError(f"Skill {skill.name} 不是模板驱动的 Skill")

        if not skill.is_active:
            raise ValueError(f"Skill {skill.name} 已被禁用")

        # 2. 检查权限
        if user_id:
            self._check_permission(skill, user_id)

        # 3. 验证输入变量
        self._validate_variables(skill, variables)

        # 4. 渲染模板
        prompt = self._render_template(skill.prompt_template, variables)
        system_prompt = skill.system_prompt or ""

        logger.info(f"执行模板 Skill: {skill.name}, 变量: {list(variables.keys())}")

        # 5. 调用 LLM（传递 user_id 以支持用户自定义配置）
        model_adapter = await self._get_model_adapter(user_id)
        with llm_context(
            task_id=task_id,
            user_id=user_id,
            project_id=project_id,
            skill_name=skill.name,
            stage=skill.display_name or skill.name
        ):
            response = model_adapter.generate(prompt, system_prompt=system_prompt)

        # 6. 解析结果
        result = self._parse_response(response, skill.output_schema)

        return {
            "skill_id": str(skill.id),
            "skill_name": skill.name,
            "result": result,
            "raw_response": response
        }

    async def _load_skill(self, skill_id: str) -> Optional[Skill]:
        """从数据库加载 Skill"""
        try:
            skill_uuid = UUID(skill_id)
        except ValueError:
            logger.error(f"无效的 Skill ID 格式: {skill_id}")
            return None

        stmt = select(Skill).where(Skill.id == skill_uuid)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    def _check_permission(self, skill: Skill, user_id: str) -> None:
        """检查用户是否有权限执行该 Skill"""
        if skill.visibility == "public":
            return

        if str(skill.owner_id) == user_id:
            return

        if skill.visibility == "shared":
            allowed_users = skill.allowed_users or []
            if user_id in allowed_users:
                return

        raise PermissionError(f"用户 {user_id} 无权执行 Skill {skill.name}")

    def _validate_variables(self, skill: Skill, variables: Dict[str, Any]) -> None:
        """验证输入变量是否完整"""
        input_variables = skill.input_variables or []

        for var_def in input_variables:
            var_name = var_def if isinstance(var_def, str) else var_def.get("name")
            required = True if isinstance(var_def, str) else var_def.get("required", True)

            if required and var_name not in variables:
                raise ValueError(f"缺少必需的变量: {var_name}")

    def _render_template(self, template: str, variables: Dict[str, Any]) -> str:
        """渲染模板，替换 {{variable}} 变量

        Args:
            template: 包含 {{variable}} 占位符的模板字符串
            variables: 变量字典

        Returns:
            替换后的字符串
        """
        if not template:
            raise ValueError("模板内容为空")

        def replace_var(match):
            var_name = match.group(1).strip()
            if var_name in variables:
                value = variables[var_name]
                # 如果是字典或列表，转换为 JSON 字符串
                if isinstance(value, (dict, list)):
                    return json.dumps(value, ensure_ascii=False, indent=2)
                return str(value)
            # 未找到变量时保留原始占位符
            logger.warning(f"模板变量未找到: {var_name}")
            return match.group(0)

        # 匹配 {{variable}} 格式
        pattern = r"\{\{\s*(\w+)\s*\}\}"
        return re.sub(pattern, replace_var, template)

    def _parse_response(
        self,
        response: str,
        output_schema: Optional[Dict[str, Any]]
    ) -> Any:
        """解析 LLM 响应

        Args:
            response: LLM 原始响应
            output_schema: 期望的输出格式定义

        Returns:
            解析后的结果
        """
        if not response:
            return None

        # 尝试提取 JSON
        json_result = self._extract_json(response)

        if json_result is not None:
            return json_result

        # 如果没有 output_schema，返回原始文本
        if not output_schema:
            return response.strip()

        # 有 schema 但解析失败，记录警告
        logger.warning(f"JSON 解析失败，返回原始文本。响应前500字符: {response[:500]}")
        return response.strip()

    def _extract_json(self, text: str) -> Optional[Any]:
        """从文本中提取 JSON

        支持以下格式：
        1. 纯 JSON 文本
        2. ```json ... ``` 代码块
        3. 文本中嵌入的 JSON 对象或数组
        """
        # 1. 尝试直接解析
        try:
            return json.loads(text.strip())
        except json.JSONDecodeError:
            pass

        # 2. 尝试提取 ```json ... ``` 代码块
        json_block_pattern = r"```(?:json)?\s*([\s\S]*?)```"
        matches = re.findall(json_block_pattern, text)
        for match in matches:
            try:
                return json.loads(match.strip())
            except json.JSONDecodeError:
                continue

        # 3. 尝试提取 JSON 对象 {...}
        obj_pattern = r"\{[\s\S]*\}"
        obj_matches = re.findall(obj_pattern, text)
        for match in obj_matches:
            try:
                return json.loads(match)
            except json.JSONDecodeError:
                continue

        # 4. 尝试提取 JSON 数组 [...]
        arr_pattern = r"\[[\s\S]*\]"
        arr_matches = re.findall(arr_pattern, text)
        for match in arr_matches:
            try:
                return json.loads(match)
            except json.JSONDecodeError:
                continue

        return None
