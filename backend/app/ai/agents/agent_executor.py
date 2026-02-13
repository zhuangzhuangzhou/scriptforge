import re
import json
import time
from typing import Any, Dict, Optional
from app.ai.adapters.base import BaseAdapter


class AgentExecutor:
    """Agent 执行器 - 动态加载和执行 Agent"""

    def __init__(self, model_adapter: BaseAdapter):
        self.model_adapter = model_adapter
        self.execution_history = []

    async def execute(
        self,
        agent_definition: Dict[str, Any],
        input_data: Any,
        context: Optional[Dict[str, Any]] = None,
        parameters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        执行 Agent

        Args:
            agent_definition: Agent 定义信息
            input_data: 输入数据
            context: 上下文数据
            parameters: 运行参数

        Returns:
            执行结果
        """
        parameters = parameters or {}

        start_time = time.time()

        # 1. 构建完整的 prompt
        full_prompt = self._build_prompt(
            agent_definition=agent_definition,
            input_data=input_data,
            context=context,
            parameters=parameters
        )

        # 2. 获取系统提示词
        system_prompt = agent_definition.get("system_prompt", "")
        if not system_prompt:
            system_prompt = self._build_system_prompt(agent_definition)

        # 3. 调用模型生成
        try:
            response = await self.model_adapter.generate(
                prompt=full_prompt,
                system_prompt=system_prompt,
                temperature=parameters.get("temperature", 0.7),
                max_tokens=parameters.get("max_tokens", 100000)
            )

            # 4. 解析结果
            result = self._parse_response(
                response=response,
                output_format=agent_definition.get("output_format", "text")
            )

            execution_time = int((time.time() - start_time) * 1000)
            tokens_used = response.get("usage", {}).get("total_tokens", 0) if isinstance(response, dict) else 0

            return {
                "success": True,
                "output": result,
                "tokens_used": tokens_used,
                "execution_time": execution_time,
                "raw_response": response if isinstance(response, str) else response.get("content", "")
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__
            }

    def _build_system_prompt(self, agent_definition: Dict[str, Any]) -> str:
        """构建系统提示词"""
        parts = []

        # 角色设定
        role = agent_definition.get("role", "")
        if role:
            parts.append(f"# 角色\n{role}")

        # 目标
        goal = agent_definition.get("goal", "")
        if goal:
            parts.append(f"# 目标\n{goal}")

        return "\n\n".join(parts)

    def _build_prompt(
        self,
        agent_definition: Dict[str, Any],
        input_data: Any,
        context: Optional[Dict[str, Any]] = None,
        parameters: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        构建完整 prompt

        支持的变量：
        - {{input}} - 输入数据
        - {{context}} - 上下文数据
        - {{input_key}} - 输入数据的特定字段
        - {{param_key}} - 参数值
        """
        template = agent_definition.get("prompt_template", "{{input}}")
        parameters = parameters or {}

        # 转换输入数据为字符串
        if isinstance(input_data, dict):
            input_str = json.dumps(input_data, ensure_ascii=False, indent=2)
        elif isinstance(input_data, str):
            input_str = input_data
        else:
            input_str = str(input_data)

        # 转换上下文数据
        context_str = ""
        if context:
            if isinstance(context, dict):
                context_str = json.dumps(context, ensure_ascii=False, indent=2)
            else:
                context_str = str(context)

        # 构建变量字典
        variables = {
            "input": input_str,
            "context": context_str
        }

        # 添加输入数据的字段
        if isinstance(input_data, dict):
            for key, value in input_data.items():
                variables[f"input_{key}"] = str(value)

        # 添加参数
        for key, value in parameters.items():
            variables[f"param_{key}"] = str(value)

        # 替换模板中的变量
        prompt = template
        for key, value in variables.items():
            # 支持 {{key}} 和 {{ key }} 两种格式
            prompt = prompt.replace(f"{{{{{key}}}}}", str(value))
            prompt = prompt.replace(f"{{ {key} }}", str(value))

        return prompt

    def _parse_response(
        self,
        response: Any,
        output_format: str = "text"
    ) -> Any:
        """解析 Agent 输出"""
        # 提取文本内容
        if isinstance(response, dict):
            content = response.get("content", "")
        else:
            content = response

        if not content:
            return content

        # 根据输出格式解析
        if output_format == "json":
            return self._extract_json(content)
        elif output_format == "structured":
            return self._extract_structured(content)
        else:
            return content.strip()

    def _extract_json(self, content: str) -> Dict[str, Any]:
        """从文本中提取 JSON"""
        # 尝试直接解析
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass

        # 尝试从代码块中提取
        json_pattern = r'```(?:json)?\s*([\s\S]*?)\s*```'
        matches = re.findall(json_pattern, content, re.IGNORECASE)

        for match in matches:
            try:
                return json.loads(match.strip())
            except json.JSONDecodeError:
                continue

        # 尝试找到 {...} 或 [...] 格式
        brace_pattern = r'\{[\s\S]*\}|\[[\s\S]*\]'
        matches = re.findall(brace_pattern, content)

        for match in matches:
            try:
                return json.loads(match)
            except json.JSONDecodeError:
                continue

        # 返回原始内容
        return {"raw": content.strip()}

    def _extract_structured(self, content: str) -> Dict[str, Any]:
        """从文本中提取结构化数据"""
        result = {
            "content": content.strip(),
            "summary": "",
            "key_points": [],
            "suggestions": []
        }

        # 提取摘要
        summary_pattern = r'(?:摘要|总结|summary)[:：]\s*(.+?)(?:\n\n|$)'
        match = re.search(summary_pattern, content, re.IGNORECASE | re.DOTALL)
        if match:
            result["summary"] = match.group(1).strip()

        # 提取关键点
        points_pattern = r'(?:关键点|要点|key points?)[：:\s*\n]+([\s\S]*?)(?=\n\n|$)'
        match = re.search(points_pattern, content, re.IGNORECASE | re.DOTALL)
        if match:
            points_text = match.group(1)
            # 解析列表
            points = re.findall(r'[-•*]\s*(.+?)(?:\n|$)', points_text)
            result["key_points"] = [p.strip() for p in points if p.strip()]

        # 提取建议
        suggestions_pattern = r'(?:建议|改进|suggestions?)[：:\s*\n]+([\s\S]*?)(?=\n\n|$)'
        match = re.search(suggestions_pattern, content, re.IGNORECASE | re.DOTALL)
        if match:
            suggestions_text = match.group(1)
            suggestions = re.findall(r'[-•*]\s*(.+?)(?:\n|$)', suggestions_text)
            result["suggestions"] = [s.strip() for s in suggestions if s.strip()]

        return result

    def get_execution_history(self) -> list:
        """获取执行历史"""
        return self.execution_history

    def clear_history(self):
        """清空执行历史"""
        self.execution_history = []
