"""测试 Breakdown Worker 实现

这些测试验证拆解逻辑的核心功能。
"""
import pytest
from unittest.mock import Mock, MagicMock
from app.tasks.breakdown_tasks import (
    _format_chapters_sync,
    _parse_json_response_sync,
    _extract_conflicts_sync,
)


class TestFormatChapters:
    """测试章节格式化"""
    
    def test_format_single_chapter(self):
        """测试格式化单个章节"""
        chapter = Mock()
        chapter.chapter_number = 1
        chapter.title = "开始"
        chapter.content = "这是第一章的内容"
        
        result = _format_chapters_sync([chapter])
        
        assert "第 1 章：开始" in result
        assert "这是第一章的内容" in result
    
    def test_format_multiple_chapters(self):
        """测试格式化多个章节"""
        chapters = []
        for i in range(1, 4):
            chapter = Mock()
            chapter.chapter_number = i
            chapter.title = f"第{i}章"
            chapter.content = f"内容{i}"
            chapters.append(chapter)
        
        result = _format_chapters_sync(chapters)
        
        assert "第 1 章：第1章" in result
        assert "第 2 章：第2章" in result
        assert "第 3 章：第3章" in result
    
    def test_format_chapter_without_title(self):
        """测试没有标题的章节"""
        chapter = Mock()
        chapter.chapter_number = 5
        chapter.title = None
        chapter.content = "内容"
        
        result = _format_chapters_sync([chapter])
        
        assert "第 5 章" in result


class TestParseJsonResponse:
    """测试 JSON 响应解析"""
    
    def test_parse_valid_json_array(self):
        """测试解析有效的 JSON 数组"""
        response = '[{"type": "冲突", "description": "测试"}]'
        result = _parse_json_response_sync(response)
        
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["type"] == "冲突"
    
    def test_parse_valid_json_object(self):
        """测试解析有效的 JSON 对象"""
        response = '{"status": "success", "data": []}'
        result = _parse_json_response_sync(response)
        
        assert isinstance(result, dict)
        assert result["status"] == "success"
    
    def test_parse_json_code_block(self):
        """测试解析 JSON 代码块"""
        response = '''
这是一些文字
```json
[{"type": "冲突"}]
```
更多文字
'''
        result = _parse_json_response_sync(response)
        
        assert isinstance(result, list)
        assert len(result) == 1
    
    def test_parse_json_embedded_in_text(self):
        """测试从文本中提取 JSON"""
        response = '这是一些文字 [{"type": "冲突"}] 更多文字'
        result = _parse_json_response_sync(response)
        
        assert isinstance(result, list)
        assert len(result) == 1
    
    def test_parse_invalid_json_returns_default(self):
        """测试解析失败返回默认值"""
        response = 'this is not json at all'
        result = _parse_json_response_sync(response, default=[])
        
        assert result == []
    
    def test_parse_empty_string_returns_default(self):
        """测试空字符串返回默认值"""
        response = ''
        result = _parse_json_response_sync(response, default={"error": "empty"})
        
        assert result == {"error": "empty"}


class TestExtractConflicts:
    """测试冲突提取"""
    
    def test_extract_conflicts_success(self):
        """测试成功提取冲突"""
        # Mock 模型适配器
        model_adapter = Mock()
        model_adapter.generate.return_value = '''
[
  {
    "type": "人物冲突",
    "description": "主角与反派的对抗",
    "participants": ["主角", "反派"],
    "intensity": 8,
    "chapter_range": [1, 3]
  }
]
'''
        
        chapters_text = "测试章节内容"
        task_config = {}
        
        result = _extract_conflicts_sync(chapters_text, model_adapter, task_config)
        
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["type"] == "人物冲突"
        assert result[0]["intensity"] == 8
        
        # 验证调用了模型
        model_adapter.generate.assert_called_once()
        call_args = model_adapter.generate.call_args[0][0]
        assert "测试章节内容" in call_args
    
    def test_extract_conflicts_model_error(self):
        """测试模型调用失败"""
        # Mock 模型适配器抛出异常
        model_adapter = Mock()
        model_adapter.generate.side_effect = Exception("API Error")
        
        chapters_text = "测试章节内容"
        task_config = {}
        
        result = _extract_conflicts_sync(chapters_text, model_adapter, task_config)
        
        # 应该返回空列表而不是抛出异常
        assert result == []
    
    def test_extract_conflicts_invalid_json(self):
        """测试模型返回无效 JSON"""
        model_adapter = Mock()
        model_adapter.generate.return_value = "这不是有效的 JSON"
        
        chapters_text = "测试章节内容"
        task_config = {}
        
        result = _extract_conflicts_sync(chapters_text, model_adapter, task_config)
        
        # 应该返回空列表
        assert result == []


class TestPromptConstruction:
    """测试提示词构建"""
    
    def test_conflict_prompt_includes_chapters(self):
        """测试冲突提示词包含章节内容"""
        model_adapter = Mock()
        model_adapter.generate.return_value = "[]"
        
        chapters_text = "这是测试章节内容，包含特殊标记 XYZ123"
        task_config = {}
        
        _extract_conflicts_sync(chapters_text, model_adapter, task_config)
        
        # 验证提示词包含章节内容
        call_args = model_adapter.generate.call_args[0][0]
        assert "XYZ123" in call_args
        assert "章节内容" in call_args
    
    def test_conflict_prompt_requests_json_format(self):
        """测试冲突提示词要求 JSON 格式"""
        model_adapter = Mock()
        model_adapter.generate.return_value = "[]"
        
        chapters_text = "测试内容"
        task_config = {}
        
        _extract_conflicts_sync(chapters_text, model_adapter, task_config)
        
        # 验证提示词要求 JSON 格式
        call_args = model_adapter.generate.call_args[0][0]
        assert "JSON" in call_args or "json" in call_args
        assert "数组" in call_args


# 集成测试标记
@pytest.mark.integration
class TestBreakdownIntegration:
    """集成测试（需要真实数据库）"""
    
    @pytest.mark.skip(reason="需要真实数据库和模型适配器")
    def test_full_breakdown_flow(self, db_session, test_project, test_batch):
        """测试完整的拆解流程"""
        # 这个测试需要：
        # 1. 真实的数据库会话
        # 2. 测试项目和批次
        # 3. 测试章节数据
        # 4. Mock 或真实的模型适配器
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
