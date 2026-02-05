# 修复 JSON 解析错误处理

## Goal
改进 AI 模块中的 JSON 解析错误处理，添加日志记录，避免错误被静默吞掉。

## Requirements

### 问题位置
1. `backend/app/ai/graph/breakdown_nodes.py` - 多处裸 except
2. `backend/app/ai/skills/*.py` - 所有 Skill 文件的 JSON 解析

### 修复方案
1. 将裸 `except` 改为 `except json.JSONDecodeError`
2. 添加 logging 记录错误信息
3. 记录原始响应内容便于调试

## Acceptance Criteria

- [ ] breakdown_nodes.py 错误处理完善
- [ ] 所有 Skill 文件错误处理完善
- [ ] 添加适当的日志记录
- [ ] 代码语法检查通过
