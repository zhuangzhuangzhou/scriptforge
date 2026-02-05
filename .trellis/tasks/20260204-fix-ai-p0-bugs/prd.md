# 修复 AI 模块 P0 阻塞性 Bug

## Goal
修复 AI 模块中的阻塞性 bug，确保系统可以正常运行。

## Requirements

### Bug 1: ConsistencyCheck 模型不存在
- 文件: `backend/app/models/consistency_check.py` 不存在
- 影响: `consistency_checker.py` 导入失败
- 修复: 创建 ConsistencyCheck 模型

### Bug 2: orchestrator.py 导入错误
- 文件: `backend/app/ai/agents/orchestrator.py` 第 17 行
- 问题: `from app.ai.adapters.base import BaseAdapter`
- 实际: 基类名为 `BaseModelAdapter`
- 修复: 更正导入语句

### Bug 3: get_adapter() 参数问题
- 文件: `backend/app/ai/adapters/__init__.py`
- 问题: `get_adapter()` 调用 `OpenAIAdapter()` 未传入 api_key
- 修复: 添加参数传递或使用配置

## Acceptance Criteria

- [ ] ConsistencyCheck 模型创建完成
- [ ] orchestrator.py 导入错误修复
- [ ] get_adapter() 可以正确获取适配器
- [ ] 代码语法检查通过
