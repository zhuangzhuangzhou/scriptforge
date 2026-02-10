# Breakdown API 端点参考

**版本**: v1  
**基础路径**: `/api/v1/breakdown`

---

## 端点列表

### 1. 启动拆解任务

#### POST /breakdown/start
启动单个批次的剧情拆解任务

**请求体**:
```json
{
  "batch_id": "uuid",
  "selected_skills": ["skill1", "skill2"],  // 可选
  "pipeline_id": "uuid",  // 可选
  "adapt_method_key": "adapt_method_default",  // 可选
  "quality_rule_key": "qa_breakdown_default",  // 可选
  "output_style_key": "output_style_default"  // 可选
}
```

**响应**:
```json
{
  "task_id": "uuid",
  "status": "queued"
}
```

**错误码**:
- `404` - 批次不存在或无权访问
- `400` - 项目未配置拆解模型
- `409` - 该批次已有任务在执行中
- `403` - 剧集配额已用尽
- `503` - 任务队列服务不可用

---

#### POST /breakdown/continue/{project_id}
继续拆解：从第一个 pending 批次开始

**路径参数**:
- `project_id`: 项目 ID

**响应**:
```json
{
  "task_id": "uuid",
  "batch_id": "uuid",
  "status": "queued"
}
```

或者（没有待拆解批次）:
```json
{
  "task_id": null,
  "batch_id": null,
  "message": "没有待拆解的批次"
}
```

**错误码**: 与 `/start` 相同

---

#### POST /breakdown/start-all
批量启动所有 pending 批次

**查询参数**:
- `project_id`: 项目 ID

**响应**:
```json
{
  "task_ids": ["uuid1", "uuid2", ...],
  "total": 5
}
```

或者（部分失败）:
```json
{
  "task_ids": ["uuid1", "uuid2"],
  "total": 2,
  "failed": 3,
  "message": "成功启动 2 个任务，3 个失败"
}
```

**错误码**:
- `404` - 项目不存在或无权访问
- `400` - 项目未配置拆解模型
- `409` - 部分批次已有任务在执行中
- `403` - 剧集配额已用尽或配额不足

---

#### POST /breakdown/batch-start
批量启动拆解（增强版，支持自定义配置）

**请求体**:
```json
{
  "project_id": "uuid",
  "adapt_method_key": "adapt_method_default",  // 可选
  "quality_rule_key": "qa_breakdown_default",  // 可选
  "output_style_key": "output_style_default",  // 可选
  "concurrent_limit": 3  // 可选，默认 3，范围 1-10
}
```

**响应**:
```json
{
  "task_ids": ["uuid1", "uuid2", ...],
  "total": 5,
  "project_id": "uuid",
  "config": {
    "adapt_method_key": "adapt_method_default",
    "quality_rule_key": "qa_breakdown_default",
    "output_style_key": "output_style_default"
  },
  "message": "已启动 5 个拆解任务"
}
```

**特点**:
- 处理所有 `pending` 或 `failed` 状态的批次
- 支持自定义配置参数
- 支持并发控制

**错误码**: 与 `/start-all` 相同

---

### 2. 查询任务状态

#### GET /breakdown/tasks/{task_id}
获取拆解任务状态

**路径参数**:
- `task_id`: 任务 ID

**响应**:
```json
{
  "task_id": "uuid",
  "status": "running",
  "progress": 45,
  "current_step": "正在分析剧情冲突...",
  "error_message": null,
  "error_display": null,
  "retry_count": 0,
  "depends_on": []
}
```

**status 可能的值**:
- `queued` - 排队中
- `running` - 执行中
- `retrying` - 重试中
- `completed` - 已完成
- `failed` - 失败

**error_display 结构**（当任务失败时）:
```json
{
  "title": "系统配置问题",
  "description": "后台任务执行环境配置异常",
  "suggestion": "请联系技术支持或稍后重试",
  "icon": "⚙️",
  "severity": "error",
  "failed_at": "2026-02-10 12:34:56",
  "retry_count": 1,
  "technical_details": "..."
}
```

---

#### GET /breakdown/tasks/{task_id}/logs
获取任务执行日志（包括 LLM 调用详情）

**路径参数**:
- `task_id`: 任务 ID

**响应**:
```json
{
  "task_id": "uuid",
  "execution_id": "uuid",
  "execution_logs": [
    {
      "timestamp": "2026-02-10T12:34:56Z",
      "stage": "conflict_analysis",
      "event": "stage_start",
      "message": "开始分析剧情冲突",
      "detail": {}
    }
  ],
  "llm_calls": {
    "total": 5,
    "stages": [
      {
        "stage": "conflict_analysis",
        "validator": "conflict_validator",
        "status": "passed",
        "score": 0.95,
        "timestamp": "2026-02-10T12:35:00Z"
      }
    ]
  },
  "timeline": [...]
}
```

---

#### GET /breakdown/batch-progress/{project_id}
获取项目批量拆解进度

**路径参数**:
- `project_id`: 项目 ID

**响应**:
```json
{
  "project_id": "uuid",
  "total_batches": 10,
  "completed": 5,
  "in_progress": 2,
  "pending": 2,
  "failed": 1,
  "overall_progress": 50.0,
  "status_summary": {
    "pending": 2,
    "queued": 1,
    "running": 1,
    "retrying": 0,
    "completed": 5,
    "failed": 1
  },
  "task_details": [
    {
      "batch_id": "uuid",
      "batch_number": 1,
      "batch_status": "completed",
      "chapter_count": 5,
      "task_id": "uuid",
      "task_status": "completed",
      "progress": 100,
      "current_step": "已完成",
      "retry_count": 0,
      "error_message": null
    }
  ],
  "last_updated": "2026-02-10T12:34:56Z"
}
```

---

### 3. 获取拆解结果

#### GET /breakdown/results/{batch_id}
获取批次的拆解结果

**路径参数**:
- `batch_id`: 批次 ID

**响应**:
```json
{
  "batch_id": "uuid",
  "conflicts": [...],
  "plot_hooks": [...],
  "characters": [...],
  "scenes": [...],
  "emotions": [...],
  "consistency_status": "passed",
  "consistency_score": 0.95,
  "consistency_results": {...},
  "qa_status": "passed",
  "qa_report": {...},
  "used_adapt_method_id": "uuid"
}
```

---

### 4. 配置管理

#### GET /breakdown/available-configs
获取拆解可用的配置列表

**响应**:
```json
{
  "adapt_methods": [
    {
      "key": "adapt_method_default",
      "description": "默认改编方法",
      "is_custom": false
    }
  ],
  "quality_rules": [
    {
      "key": "qa_breakdown_default",
      "description": "默认质量规则",
      "is_custom": false
    }
  ],
  "output_styles": [
    {
      "key": "output_style_default",
      "description": "默认输出风格",
      "is_custom": false
    }
  ]
}
```

---

### 5. 任务重试

#### POST /breakdown/tasks/{task_id}/retry
重试失败的任务

**路径参数**:
- `task_id`: 任务 ID

**请求体**（可选）:
```json
{
  "new_config": {
    "adapt_method_key": "adapt_method_custom",
    "quality_rule_key": "qa_breakdown_strict"
  }
}
```

**响应**:
```json
{
  "task_id": "new_uuid",
  "status": "queued",
  "retry_count": 1,
  "batch_id": "uuid",
  "config": {...},
  "message": "任务已重新加入队列（第 1 次尝试）"
}
```

**限制**:
- 只能重试 `failed` 状态的任务
- 最多重试 3 次
- 需要有足够的配额

**错误码**:
- `404` - 任务不存在
- `400` - 任务状态不是 failed 或已重试 3 次
- `403` - 剧集配额已用尽

---

## 事务管理说明

### 单批次操作 (`/start`, `/continue`)
- 使用手动事务管理
- Celery 失败时调用 `await db.rollback()` 回滚所有更改
- 成功时调用 `await db.commit()` 提交事务

### 批量操作 (`/start-all`, `/batch-start`)
- 先创建任务，Celery 成功后才消耗配额
- Celery 失败时删除任务记录，不消耗配额
- 部分失败不影响其他批次
- 最终提交只包含成功批次的更改

---

## 配额管理

### 检查配额
所有启动端点都会检查用户的剧集配额：
- 使用 `with_for_update()` 锁定用户记录，防止并发问题
- 检查配额是否足够
- 配额不足时返回 403 错误

### 消耗配额
- **单批次**: 预扣配额，失败时回滚
- **批量**: Celery 成功后才消耗配额，失败时不消耗

### 配额退还
- 任务失败时，配额会在 Celery worker 中自动退还
- 详见 `backend/app/tasks/breakdown_tasks.py`

---

## 错误处理

### 人性化错误信息
所有任务失败时，会生成人性化的错误信息：
- `title`: 错误标题
- `description`: 错误描述
- `suggestion`: 解决建议
- `icon`: 错误图标
- `severity`: 严重程度（error/warning）
- `technical_details`: 技术细节（截断到 200 字符）

### 常见错误类型
- `greenlet_spawn`: 系统配置问题
- `QUOTA_EXCEEDED`: 配额不足
- `MODEL_ERROR`: AI 模型错误
- `NETWORK_ERROR`: 网络连接问题
- `TIMEOUT`: 处理超时
- `PERMISSION_DENIED`: 权限不足
- `DATA_NOT_FOUND`: 数据不存在

---

## 相关文档

- [修复报告](./BREAKDOWN_API_FINAL_FIX.md)
- [问题分析](./BREAKDOWN_API_ISSUES.md)
- [Celery 修复](./CELERY_FIX_SUMMARY.md)

---

**最后更新**: 2026-02-10
