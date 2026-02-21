# Agent 拆解流程 QA 测试报告

## 测试概述

- 测试目标：验证 `/breakdown/start` 接口的完整拆解流程
- 测试脚本：`backend/test_breakdown_qa.py`
- 测试时间：2026-02-19

## 测试环境要求

1. 后端服务运行：`cd backend && uvicorn app.main:app --reload`
2. Celery Worker 运行：`cd backend && celery -A app.core.celery_app worker -l info`
3. Redis 服务运行
4. PostgreSQL 数据库运行
5. 测试数据准备：需要有 project 和 batch（含 chapter）数据

## 测试用例列表

### 场景1：skill_only 模式

| 项目 | 内容 |
|------|------|
| 输入 | `execution_mode: "skill_only"` |
| 预期流程 | Skill 直接调用 → QA 质检 → 结果保存 |
| 验证点 | 1. `plot_breakdown.qa_status` 有值 (PASS/FAIL) |
|        | 2. `plot_breakdown.qa_score` 有值 (0-100) |
|        | 3. `plot_breakdown.plot_points` 有剧情点数据 |
| 特点 | 不走 Agent 工作流，直接调用 webtoon_breakdown Skill |

### 场景2：agent_single 模式

| 项目 | 内容 |
|------|------|
| 输入 | `execution_mode: "agent_single"` |
| 预期流程 | Agent 单轮执行 → QA 质检 → 自动修正（如需要） |
| 验证点 | 1. Agent 只执行 1 轮（max_iterations_override=1） |
|        | 2. 质检不通过时触发外部自动修正循环 |
|        | 3. 修正最多 3 次 |
| 特点 | 推荐模式，平衡质量和 Token 消耗 |

### 场景3：agent_loop 模式

| 项目 | 内容 |
|------|------|
| 输入 | `execution_mode: "agent_loop"` |
| 预期流程 | Agent 内部循环（breakdown → qa → 修正，最多3轮） |
| 验证点 | 1. 质检通过后退出循环 |
|        | 2. 最多执行 3 轮 |
|        | 3. 禁用外部自动修正 |
| 特点 | Token 消耗较大，每轮全量重生成 |

### 场景4：资源加载测试

| 项目 | 内容 |
|------|------|
| 输入 | `resource_ids: []` 或 `resource_ids: ["uuid1", "uuid2"]` |
| 验证点 | 1. 不选择资源时加载系统默认（hook_types, hook_rules 等） |
|        | 2. 选择资源时正确传递给 Skill prompt |
| 资源分类 | hook_types, hook_rules, qa_dimensions, type_guide |

### 场景5：取消任务测试

| 项目 | 内容 |
|------|------|
| 接口 | `POST /breakdown/tasks/{task_id}/stop` |
| 验证点 | 1. 任务状态变为 `cancelling` → `cancelled` |
|        | 2. 批次状态重置为 `pending` |
|        | 3. 配额返还 |
|        | 4. 后续排队任务一并取消 |

### 场景6：进度报告测试

| 项目 | 内容 |
|------|------|
| 接口 | `GET /breakdown/tasks/{task_id}` |
| 验证点 | 1. `progress` 实时更新 (0-100) |
|        | 2. `current_step` 有具体步骤描述 |
|        | 3. `status` 状态正确转换 |

## API 接口说明

### 启动拆解

```
POST /api/v1/breakdown/start
```

请求体：
```json
{
  "batch_id": "uuid",
  "execution_mode": "skill_only | agent_single | agent_loop",
  "resource_ids": ["uuid1", "uuid2"],  // 可选
  "novel_type": "webnovel"  // 可选
}
```

响应：
```json
{
  "task_id": "uuid",
  "status": "queued"
}
```

### 查询任务状态

```
GET /api/v1/breakdown/tasks/{task_id}
```

响应：
```json
{
  "task_id": "uuid",
  "status": "queued | running | completed | failed | cancelled",
  "progress": 50,
  "current_step": "剧集拆解中...",
  "error_message": null
}
```

### 获取拆解结果

```
GET /api/v1/breakdown/results/{batch_id}
```

响应（format_version >= 2）：
```json
{
  "id": "uuid",
  "batch_id": "uuid",
  "format_version": 3,
  "plot_points": [
    {
      "id": 1,
      "scene": "酒店大堂",
      "characters": ["林浩", "陈总"],
      "event": "林浩揭穿欺诈",
      "hook_type": "打脸爽点",
      "episode": 1,
      "status": "unused"
    }
  ],
  "qa_status": "PASS",
  "qa_score": 85,
  "qa_report": {...}
}
```

### 停止任务

```
POST /api/v1/breakdown/tasks/{task_id}/stop
```

响应：
```json
{
  "task_id": "uuid",
  "status": "cancelling",
  "cancelled_count": 1,
  "message": "已停止任务"
}
```

## 执行模式对比

| 模式 | Agent 轮数 | 外部修正 | Token 消耗 | 适用场景 |
|------|-----------|---------|-----------|---------|
| skill_only | 0 | 是（最多3次） | 低 | 快速测试 |
| agent_single | 1 | 是（最多3次） | 中 | 推荐使用 |
| agent_loop | 最多3 | 否 | 高 | 高质量要求 |

## 数据库表结构

### plot_breakdowns 表关键字段

| 字段 | 类型 | 说明 |
|------|------|------|
| plot_points | JSONB | 剧情点列表（解析后的 JSON） |
| plot_points_raw | TEXT | 原始结构化文本（用于调试） |
| format_version | INT | 1=旧格式, 2=JSON格式, 3=结构化文本 |
| qa_status | VARCHAR | PASS / FAIL / pending |
| qa_score | INT | 0-100 |
| qa_report | JSONB | 质检报告详情 |
| qa_retry_count | INT | 质检重试次数 |

## 运行测试

```bash
cd backend
python test_breakdown_qa.py
```

## 已知问题

1. 后端服务未运行时测试会失败
2. 需要有效的 AI 模型配置（model_config_id）
3. 需要有章节数据的批次才能测试拆解

## 改进建议

1. 添加 Mock 模型响应支持，便于离线测试
2. 增加 WebSocket 实时日志测试
3. 增加并发测试场景
4. 增加性能基准测试（Token 消耗、耗时统计）
