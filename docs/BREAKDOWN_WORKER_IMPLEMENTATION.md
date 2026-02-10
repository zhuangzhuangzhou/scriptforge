# Breakdown Worker 实现总结

## 概述

本文档说明了 `run_breakdown_task` Celery Worker 中剧情拆解逻辑的实现。

## 实现方案

采用**简化直接**的方案：直接在 `breakdown_tasks.py` 中实现拆解逻辑，不创建额外的 Executor 类。

### 为什么选择这个方案？

1. **避免过度设计**：不需要创建额外的抽象层
2. **代码更清晰**：所有逻辑都在一个文件中，易于理解和维护
3. **避免同步/异步混淆**：所有代码都是纯同步的

## 核心实现

### 文件位置
`backend/app/tasks/breakdown_tasks.py`

### 主要函数

#### 1. `run_breakdown_task` (Celery 任务入口)
```python
@celery_app.task(**CELERY_TASK_CONFIG)
def run_breakdown_task(self, task_id, batch_id, project_id, user_id):
    """Celery 任务入口"""
    # 1. 初始化数据库会话
    # 2. 获取模型适配器
    # 3. 执行拆解逻辑
    # 4. 错误处理和重试
```

#### 2. `_execute_breakdown_sync` (拆解主逻辑)
```python
def _execute_breakdown_sync(db, task_id, batch_id, project_id, model_adapter, task_config):
    """执行拆解的主要逻辑"""
    # 1. 加载章节数据
    # 2. 格式化章节文本
    # 3. 执行 5 个拆解技能：
    #    - 提取冲突
    #    - 识别情节钩子
    #    - 分析角色
    #    - 识别场景
    #    - 提取情感
    # 4. 保存拆解结果到 PlotBreakdown 表
```

#### 3. 拆解技能函数

每个技能都是一个独立的函数：

- `_extract_conflicts_sync()` - 提取冲突
- `_identify_plot_hooks_sync()` - 识别情节钩子
- `_analyze_characters_sync()` - 分析角色
- `_identify_scenes_sync()` - 识别场景
- `_extract_emotions_sync()` - 提取情感

每个函数的工作流程：
1. 构建 AI 提示词
2. 调用模型适配器生成响应
3. 解析 JSON 响应
4. 返回结构化数据

#### 4. 辅助函数

- `_format_chapters_sync()` - 格式化章节文本
- `_parse_json_response_sync()` - 解析 AI 返回的 JSON

## 执行流程

```
用户请求 /breakdown/start
    ↓
创建 AITask 记录
    ↓
启动 Celery 任务 (run_breakdown_task.delay())
    ↓
立即返回 task_id 给用户
    
    
Celery Worker 后台执行:
    ↓
1. 初始化 (0%)
    ├─ 创建同步数据库会话
    ├─ 更新任务状态为 "running"
    └─ 更新批次状态为 "processing"
    ↓
2. 获取模型适配器 (5%)
    ├─ 从任务配置读取 model_config_id
    ├─ 查询 AIModel、AIModelProvider、AIModelCredential
    └─ 创建适配器实例 (OpenAI/Anthropic/etc.)
    ↓
3. 加载章节数据 (10%)
    ├─ 从 Chapter 表查询批次的所有章节
    └─ 格式化为文本
    ↓
4. 执行拆解技能 (20% - 80%)
    ├─ 提取冲突 (20%)
    ├─ 识别情节钩子 (35%)
    ├─ 分析角色 (50%)
    ├─ 识别场景 (65%)
    └─ 提取情感 (80%)
    ↓
5. 保存结果 (90%)
    ├─ 创建 PlotBreakdown 记录
    └─ 保存到数据库
    ↓
6. 完成 (100%)
    ├─ 更新任务状态为 "completed"
    └─ 更新批次状态为 "completed"
```

## 进度更新

任务执行过程中会实时更新进度：

| 进度 | 步骤 |
|------|------|
| 0% | 初始化任务 |
| 10% | 加载章节数据 |
| 20% | 提取冲突 |
| 35% | 识别情节钩子 |
| 50% | 分析角色 |
| 65% | 识别场景 |
| 80% | 提取情感 |
| 90% | 保存拆解结果 |
| 100% | 任务完成 |

## AI 提示词设计

每个拆解技能都使用专门设计的提示词：

### 示例：提取冲突

```
你是一个专业的剧情分析师。请分析以下章节内容，提取其中的主要冲突。

章节内容：
[章节文本]

请以 JSON 数组格式返回冲突列表，每个冲突包含以下字段：
- type: 冲突类型
- description: 冲突描述
- participants: 参与者列表
- intensity: 冲突强度（1-10）
- chapter_range: 涉及的章节范围

请只返回 JSON 数组，不要包含其他文字。
```

## 数据结构

### PlotBreakdown 表结构

```python
{
    "id": "uuid",
    "batch_id": "uuid",
    "project_id": "uuid",
    "conflicts": [
        {
            "type": "人物冲突",
            "description": "主角与反派之间的权力斗争",
            "participants": ["主角", "反派"],
            "intensity": 8,
            "chapter_range": [1, 3]
        }
    ],
    "plot_hooks": [...],
    "characters": [...],
    "scenes": [...],
    "emotions": [...],
    "consistency_status": "pending",
    "qa_status": "pending",
    "used_adapt_method_id": "adapt_method_default"
}
```

## 错误处理

### 错误分类

1. **可重试错误** (`RetryableError`)
   - 网络超时
   - API 临时不可用
   - 处理：自动重试（最多 3 次，指数退避）

2. **配额不足错误** (`QuotaExceededError`)
   - API 配额用尽
   - 处理：标记失败，回滚配额，不重试

3. **其他错误** (`AITaskException`)
   - 模型配置错误
   - 数据验证失败
   - 处理：标记失败，回滚配额，不重试

### 错误处理流程

```python
try:
    # 执行拆解
    breakdown = _execute_breakdown_sync(...)
except RetryableError:
    # 更新状态为 "retrying"
    # Celery 自动重试
except QuotaExceededError:
    # 回滚配额
    # 标记失败
except AITaskException:
    # 回滚配额
    # 标记失败
```

## 配额管理

### 预扣机制

1. **API 层**：创建任务时预扣配额
2. **Worker 层**：任务失败时回滚配额
3. **TODO**：任务成功时真正扣费

```python
# API 层 (breakdown.py)
await quota_service.consume_episode_quota(user)  # 预扣

# Worker 层 (breakdown_tasks.py)
if task_failed:
    _refund_quota_sync(db, user_id)  # 回滚
```

## 性能优化建议

### 当前实现

- 所有章节一次性加载到内存
- 5 个技能串行执行
- 每个技能单独调用 AI 模型

### 未来优化方向

1. **批量处理**：将多个章节分批处理，避免超长文本
2. **并行执行**：某些技能可以并行执行（如冲突和角色分析）
3. **合并调用**：一次 AI 调用提取多个维度的信息
4. **缓存机制**：缓存已处理的章节结果

## 测试建议

### 单元测试

```python
def test_format_chapters_sync():
    """测试章节格式化"""
    chapters = [
        Chapter(chapter_number=1, title="开始", content="内容1"),
        Chapter(chapter_number=2, title="发展", content="内容2")
    ]
    result = _format_chapters_sync(chapters)
    assert "第 1 章：开始" in result
    assert "第 2 章：发展" in result

def test_parse_json_response_sync():
    """测试 JSON 解析"""
    # 测试正常 JSON
    response = '[{"type": "冲突"}]'
    result = _parse_json_response_sync(response)
    assert len(result) == 1
    
    # 测试 JSON 代码块
    response = '```json\n[{"type": "冲突"}]\n```'
    result = _parse_json_response_sync(response)
    assert len(result) == 1
    
    # 测试解析失败
    response = 'invalid json'
    result = _parse_json_response_sync(response, default=[])
    assert result == []
```

### 集成测试

```python
def test_execute_breakdown_sync(db, model_adapter):
    """测试完整拆解流程"""
    # 准备测试数据
    project = create_test_project(db)
    batch = create_test_batch(db, project.id)
    chapters = create_test_chapters(db, batch.id, count=3)
    
    # 执行拆解
    result = _execute_breakdown_sync(
        db=db,
        task_id="test-task-id",
        batch_id=str(batch.id),
        project_id=str(project.id),
        model_adapter=model_adapter,
        task_config={}
    )
    
    # 验证结果
    assert result["breakdown_id"] is not None
    assert result["conflicts_count"] >= 0
    assert result["characters_count"] >= 0
```

## 监控和日志

### 关键指标

- 任务执行时间
- 各技能执行时间
- AI 调用次数和 token 消耗
- 成功率和失败率
- 重试次数

### 日志记录

```python
# 在关键点添加日志
import logging
logger = logging.getLogger(__name__)

logger.info(f"开始拆解任务: task_id={task_id}, batch_id={batch_id}")
logger.info(f"加载了 {len(chapters)} 个章节")
logger.info(f"提取了 {len(conflicts)} 个冲突")
logger.error(f"拆解失败: {str(e)}")
```

## 相关文件

- `backend/app/tasks/breakdown_tasks.py` - Worker 实现
- `backend/app/api/v1/breakdown.py` - API 接口
- `backend/app/models/plot_breakdown.py` - 数据模型
- `backend/app/ai/adapters/__init__.py` - 模型适配器
- `backend/app/core/progress.py` - 进度更新
- `backend/app/core/exceptions.py` - 异常定义

## 总结

这个实现方案：

✅ **简单直接**：所有逻辑在一个文件中，易于理解
✅ **纯同步**：避免 greenlet 错误
✅ **可扩展**：易于添加新的拆解技能
✅ **健壮**：完善的错误处理和重试机制
✅ **可观测**：详细的进度更新和日志

下一步可以考虑：
- 添加单元测试和集成测试
- 优化 AI 提示词
- 实现批量处理和并行执行
- 添加性能监控
