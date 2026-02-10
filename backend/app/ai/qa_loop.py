"""质检循环处理器

实现拆解结果的质量检查和自动修正循环。
"""
import json
import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class QALoopHandler:
    """质检循环处理器

    负责执行质检循环，包括：
    1. 调用 breakdown_aligner 进行质量检查
    2. 根据反馈自动修正拆解结果
    3. 重试直到通过或达到最大重试次数
    4. 通过 WebSocket 实时推送质检进度
    """

    def __init__(
        self,
        db: Session,
        model_adapter,
        log_publisher=None,
        max_retries: int = 3
    ):
        """初始化质检循环处理器

        Args:
            db: 数据库会话
            model_adapter: 模型适配器
            log_publisher: Redis 日志发布器（可选）
            max_retries: 最大重试次数
        """
        self.db = db
        self.model_adapter = model_adapter
        self.log_publisher = log_publisher
        self.max_retries = max_retries

        # 加载 breakdown_aligner skill
        from app.ai.skills.breakdown_aligner_skill import BreakdownAlignerSkill
        self.breakdown_aligner = BreakdownAlignerSkill()

    async def run_with_qa(
        self,
        task_id: str,
        breakdown_data: Dict[str, Any],
        chapters: List[Any],
        adapt_method: Dict[str, Any]
    ) -> Dict[str, Any]:
        """执行带质检的拆解流程

        Args:
            task_id: 任务 ID
            breakdown_data: 拆解结果数据
            chapters: 章节列表
            adapt_method: 改编方法论配置

        Returns:
            Dict: 包含状态、数据和质检结果的字典
        """
        # 发布质检开始消息
        if self.log_publisher:
            self.log_publisher.publish_step_start(task_id, "质量检查")

        for retry in range(self.max_retries):
            # 发布重试信息
            if retry > 0 and self.log_publisher:
                self.log_publisher.publish_info(
                    task_id,
                    f"第 {retry + 1} 次质检尝试..."
                )

            # 调用 breakdown_aligner 进行质检
            qa_result = await self._check_quality(
                task_id=task_id,
                breakdown_data=breakdown_data,
                chapters=chapters,
                adapt_method=adapt_method
            )

            # 推送质检结果到 WebSocket
            await self._push_qa_progress(task_id, qa_result, retry + 1)

            # 检查是否通过
            if qa_result.get("qa_status") == "PASS":
                if self.log_publisher:
                    self.log_publisher.publish_success(
                        task_id,
                        f"✓ 质量检查通过！得分: {qa_result.get('qa_score', 0)}"
                    )
                    self.log_publisher.publish_step_end(
                        task_id,
                        "质量检查",
                        {"status": "PASS", "score": qa_result.get("qa_score", 0)}
                    )

                return {
                    "status": "success",
                    "data": breakdown_data,
                    "qa_result": qa_result,
                    "retry_count": retry
                }

            # 如果未通过且还有重试机会，尝试修正
            if retry < self.max_retries - 1:
                if self.log_publisher:
                    self.log_publisher.publish_warning(
                        task_id,
                        f"✗ 质量检查未通过，根据反馈自动修正中..."
                    )

                # 根据反馈修正拆解结果
                breakdown_data = await self._modify_based_on_feedback(
                    task_id=task_id,
                    breakdown_data=breakdown_data,
                    qa_result=qa_result,
                    chapters=chapters
                )

        # 超过最大重试次数仍未通过
        if self.log_publisher:
            self.log_publisher.publish_warning(
                task_id,
                f"⚠ 质量检查未通过（已重试 {self.max_retries} 次），标记为需人工审核"
            )
            self.log_publisher.publish_step_end(
                task_id,
                "质量检查",
                {"status": "NEEDS_REVIEW", "retry_count": self.max_retries}
            )

        return {
            "status": "needs_review",
            "data": breakdown_data,
            "qa_result": qa_result,
            "retry_count": self.max_retries
        }

    async def _check_quality(
        self,
        task_id: str,
        breakdown_data: Dict[str, Any],
        chapters: List[Any],
        adapt_method: Dict[str, Any]
    ) -> Dict[str, Any]:
        """调用 breakdown_aligner 进行质量检查

        Args:
            task_id: 任务 ID
            breakdown_data: 拆解结果数据
            chapters: 章节列表
            adapt_method: 改编方法论配置

        Returns:
            Dict: 质检结果
        """
        # 格式化章节数据
        chapters_data = [
            {
                "number": ch.chapter_number,
                "title": ch.title or f"第 {ch.chapter_number} 章",
                "content": ch.content or ""
            }
            for ch in chapters
        ]

        # 构建 context
        context = {
            "chapters": chapters_data,
            "breakdown_data": breakdown_data,
            "adapt_method": adapt_method,
            "model_adapter": self.model_adapter
        }

        try:
            # 执行质检
            result = await self.breakdown_aligner.execute(context)
            return result
        except Exception as e:
            logger.error(f"质检执行失败: {e}")
            if self.log_publisher:
                self.log_publisher.publish_error(
                    task_id,
                    f"质检执行失败: {str(e)}",
                    error_code="QA_ERROR"
                )

            return {
                "qa_status": "ERROR",
                "qa_score": 0,
                "qa_report": {
                    "error": str(e),
                    "status": "ERROR"
                }
            }

    async def _push_qa_progress(
        self,
        task_id: str,
        qa_result: Dict[str, Any],
        retry_count: int
    ):
        """推送质检进度到 WebSocket

        Args:
            task_id: 任务 ID
            qa_result: 质检结果
            retry_count: 重试次数
        """
        if not self.log_publisher:
            return

        qa_report = qa_result.get("qa_report", {})
        status = qa_result.get("qa_status", "UNKNOWN")
        score = qa_result.get("qa_score", 0)

        # 发布质检状态
        if status == "PASS":
            self.log_publisher.publish_qa_check(
                task_id=task_id,
                dimension="整体质量",
                status="pass",
                score=score,
                issues=[],
                suggestions=[]
            )
        elif status == "FAIL":
            issues = qa_report.get("issues", [])
            suggestions = qa_report.get("suggestions", [])

            self.log_publisher.publish_qa_check(
                task_id=task_id,
                dimension="整体质量",
                status="fail",
                score=score,
                issues=issues,
                suggestions=suggestions
            )

            # 发布详细的问题和建议
            if issues:
                for issue in issues[:3]:  # 只显示前3个问题
                    self.log_publisher.publish_warning(
                        task_id,
                        f"  问题: {issue}"
                    )

            if suggestions:
                for suggestion in suggestions[:3]:  # 只显示前3个建议
                    self.log_publisher.publish_info(
                        task_id,
                        f"  建议: {suggestion}"
                    )

    async def _modify_based_on_feedback(
        self,
        task_id: str,
        breakdown_data: Dict[str, Any],
        qa_result: Dict[str, Any],
        chapters: List[Any]
    ) -> Dict[str, Any]:
        """根据质检反馈修正拆解结果

        Args:
            task_id: 任务 ID
            breakdown_data: 原始拆解数据
            qa_result: 质检结果
            chapters: 章节列表

        Returns:
            Dict: 修正后的拆解数据
        """
        qa_report = qa_result.get("qa_report", {})
        issues = qa_report.get("issues", [])
        suggestions = qa_report.get("suggestions", [])

        if not suggestions:
            # 如果没有具体建议，返回原数据
            return breakdown_data

        # 构建修正提示词
        chapters_text = "\n\n".join([
            f"第{ch.chapter_number}章: {ch.title or ''}\n{ch.content or ''}"
            for ch in chapters
        ])

        prompt = f"""你是一个专业的剧情分析师。以下是一份剧情拆解结果，但质量检查发现了一些问题。

### 原始拆解结果
{json.dumps(breakdown_data, ensure_ascii=False, indent=2)}

### 质量检查反馈
**问题列表**:
{chr(10).join([f"- {issue}" for issue in issues])}

**改进建议**:
{chr(10).join([f"- {suggestion}" for suggestion in suggestions])}

### 原始章节内容
{chapters_text}

### 任务要求
请根据上述反馈，修正拆解结果。保持原有的数据结构，只修改有问题的部分。

请以 JSON 格式返回修正后的完整拆解结果，包含以下字段：
- conflicts: 冲突列表
- plot_hooks: 剧情钩子列表
- characters: 角色列表
- scenes: 场景列表
- emotions: 情感列表
- episodes: 剧集列表

请只返回 JSON，不要包含其他文字。
"""

        try:
            # 使用流式生成
            full_response = ""
            for chunk in self.model_adapter.stream_generate(prompt):
                if self.log_publisher:
                    self.log_publisher.publish_stream_chunk(
                        task_id,
                        "根据反馈修正",
                        chunk
                    )
                full_response += chunk

            # 解析修正后的结果
            modified_data = self._parse_json_response(full_response)

            if modified_data:
                if self.log_publisher:
                    self.log_publisher.publish_success(
                        task_id,
                        "✓ 修正完成，准备重新检查"
                    )
                return modified_data
            else:
                # 解析失败，返回原数据
                if self.log_publisher:
                    self.log_publisher.publish_warning(
                        task_id,
                        "⚠ 修正结果解析失败，使用原数据"
                    )
                return breakdown_data

        except Exception as e:
            logger.error(f"修正拆解结果失败: {e}")
            if self.log_publisher:
                self.log_publisher.publish_error(
                    task_id,
                    f"修正失败: {str(e)}",
                    error_code="MODIFY_ERROR"
                )
            return breakdown_data

    def _parse_json_response(self, response: str) -> Optional[Dict[str, Any]]:
        """解析 JSON 响应

        Args:
            response: AI 模型的响应文本

        Returns:
            Dict 或 None: 解析后的 JSON 对象
        """
        import re

        try:
            # 尝试直接解析
            return json.loads(response)
        except json.JSONDecodeError:
            pass

        # 尝试提取 JSON 代码块
        json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # 尝试提取任何 JSON 对象
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass

        # 解析失败
        return None
