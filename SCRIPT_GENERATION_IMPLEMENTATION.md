# 剧本生成完整功能实现文档

## 实施日期
2026-02-22

## 一、功能概述

实现了完整的剧本生成功能，包括：
- ✅ 单集剧本生成
- ✅ 批量剧本生成
- ✅ 实时日志推送（WebSocket）
- ✅ 剧本编辑与保存
- ✅ 剧本审核
- ✅ 剧本导出（PDF/DOCX）

---

## 二、后端实现

### 1. 数据模型增强 (`app/models/script.py`)

**新增字段：**
```python
status = Column(String(50), default="draft")      # 状态：draft/approved
qa_status = Column(String(50))                    # 质检状态：pass/fail
qa_score = Column(Integer)                        # 质检分数：0-100
qa_report = Column(JSONB)                         # 质检报告详情
approved_at = Column(TIMESTAMP(timezone=True))    # 审核通过时间
```

**数据库迁移：**
```bash
# 已生成迁移文件
backend/alembic/versions/6646e9d6eb5e_add_script_status_and_qa_fields.py

# 执行迁移
cd backend
alembic upgrade head
```

### 2. Celery 任务完善 (`app/tasks/script_tasks.py`)

**核心改进：**

#### 保存剧本到数据库
```python
# 检查是否已存在该集剧本
existing_script = db.query(Script).filter(
    Script.plot_breakdown_id == breakdown_id,
    Script.episode_number == episode_number
).first()

if existing_script:
    # 更新现有剧本
    existing_script.title = title
    existing_script.content = {...}
    existing_script.word_count = word_count
    existing_script.scene_count = scene_count
else:
    # 创建新剧本
    new_script = Script(...)
    db.add(new_script)

db.commit()
```

#### 日志推送增强
```python
# 任务开始
log_publisher.publish_info(task_id, "🎬 开始生成第 X 集剧本...")

# 各步骤日志
log_publisher.publish_step_start(task_id, "load_breakdown", "加载剧情拆解结果")
log_publisher.publish_step_end(task_id, "load_breakdown", {...})

# 任务完成
log_publisher.publish_task_complete(task_id, status=TaskStatus.COMPLETED, message="✅ 剧本生成完成！")
```

### 3. API 端点 (`app/api/v1/scripts.py`)

**已实现端点：**

| 方法 | 路径 | 功能 |
|------|------|------|
| POST | `/scripts/episode/start` | 启动单集剧本生成 |
| POST | `/scripts/batch/start` | 批量生成剧本 |
| GET | `/scripts/tasks/{task_id}` | 获取任务状态 |
| GET | `/scripts/episode/{breakdown_id}/{episode_number}` | 获取单集剧本 |
| GET | `/scripts/episodes/{breakdown_id}` | 获取剧本列表 |
| PUT | `/scripts/{script_id}` | 更新剧本 |
| POST | `/scripts/{script_id}/approve` | 审核通过 |

### 4. 导出功能 (`app/api/v1/export.py`)

**已实现：**
- ✅ 单集导出（PDF/DOCX）
- ✅ 批量导出（ZIP 打包）
- ✅ 中文文件名支持

---

## 三、前端实现

### 1. ScriptTab 组件增强

**新增功能：**

#### 批量生成
```typescript
const handleBatchGenerate = async () => {
  const pendingEpisodes = episodes.filter(ep => ep.status === 'pending').map(ep => ep.episode);
  const response = await scriptApi.startBatchScripts(breakdownId, pendingEpisodes, { novelType });
  // 轮询所有任务状态
  response.data.task_ids.forEach(taskId => pollTaskStatus(taskId));
}
```

#### 实时日志显示
```typescript
// 使用 useBreakdownLogs Hook
const { isConnected } = useBreakdownLogs(taskIdRef.current, {
  onStepStart: (stepName) => { /* 添加日志 */ },
  onStreamChunk: (_, chunk) => { /* 追加流式内容 */ },
  onComplete: () => { /* 加载生成的剧本 */ }
});

// 条件渲染 ConsoleLogger
{generating && (
  <ConsoleLogger
    logs={logs}
    visible={generating !== null}
    isProcessing={generating !== null}
    progress={progress}
    currentStep={currentStep}
    onClose={() => {}}
  />
)}
```

### 2. 状态管理

**核心状态：**
```typescript
// 剧集列表
episodes: Array<{ episode, status, script? }>

// 生成状态
generating: number | null
taskIdRef: Ref<string | null>

// 日志状态
logs: LogEntry[]
currentStep: string
progress: number

// 编辑状态
editMode: boolean
editedStructure: ScriptStructure | null
hasUnsavedChanges: boolean
```

---

## 四、完整交互流程

### 单集生成流程
```
用户点击"生成剧本"
  ↓
调用 startEpisodeScript API
  ↓
后端创建 AITask，启动 Celery 任务
  ↓
前端设置 taskIdRef，触发 WebSocket 连接
  ↓
Celery Worker 执行任务，推送实时日志
  ↓
前端 ConsoleLogger 显示日志
  ↓
任务完成，保存剧本到数据库
  ↓
前端加载并显示剧本
```

###生成流程
```
用户点击"批量生成全部"
  ↓
筛选待生成剧集
  ↓
调用 startBatchScripts API
  ↓
后端为每集创建独立任务
  ↓
前端轮询所有任务状态
  ↓
任务完成后刷新剧集列表
```

---

## 五、关键技术点

### 1. WebSocket 实时推送

**架构设计：**
- 复用 Breakdown 的 WebSocket 基础设施
- Redis Pub/Sub 频道：`breakdown:logs:{task_id}`
- 端点：`/api/v1/ws/breakdown-logs/{task_id}`

**消息类型：**
- `step_start` - 步骤开始
- `stream_chunk` - 流式内容片段
- `formatted_chunk` - 格式化内容
- `step_end` - 步骤结束
- `progress` - 进度更新
- `info/warning/error/success` - 各类消息
- `task_complete` - 任务完成

### 2. 日志推送分层

**三层日志推送：**
1. **任务级**：任务开始/完成
2. **步骤级**：各阶段开始/结束
3. **流式级**：LLM 实时输出（由 SimpleSkillExecutor 自动推送）

### 3. 优雅降级

**双保险机制：**
- 主要：WebSocket 实时推送
- 备份：轮询任务状态（2秒间隔）

### 4. 积分扣费

**扣费时机：**
- 任务完成后扣费，避免失败任务扣费
- 批量生成时预先检查总积分

---

## 六、测试清单

### 后端测试
- [x] 语法检查通过
- [ ] 单集剧本生成测试
- [ ] 批量剧本生成测试
- [ ] WebSocket 日志推送测试
- [ ] 剧本保存到数据库测试
- [ ] 导出功能测试

### 前端测试
- [x] TypeScript 编译通过
- [ ] 单集生成 UI 测试
- [ ] 批量生成 UI 测试
- [ ] ConsoleLogger 显示测试
- [ ] 剧本编辑功能测试
- [ ] 剧本审核功能测试

### 集成测试
- [ ] 端到端生成流程测试
- [ ] 实时日志推送测试
- [ ] 多任务并发测试
- [ ] 错误处理测试

---

## 七、部署步骤

### 1. 数据库迁移
```bash
cd backend
alembic upgrade head
```

### 2. 重启服务
```bash
# 重启 FastAPI
supervisorctl restart fastapi

# 重启 Celery Worker
supervisorctl restart celery-worker

# 重启 Redis（如需要）
sudo systemctl restart redis
```

### 3. 前端构建
```bash
cd frontend
npm run build
```

---

## 八、已知问题与改进

### 当前限制
1. 批量生成时，前端只轮询状态，不显示实时日志
2. 导出功能依赖 PDF/Word 导出器的具体实现
3. 质检功能（qa_status、qa_score）尚未实现

### 未来改进
1. **批量生成日志**：支持多任务日志聚合显示
2. **质检集成**：自动质检剧本质量
3. **版本管理**：支持剧本多版本保存
4. **协作编辑**：支持多人协作编辑剧本

---

## 九、相关文件清单

### 后端文件
```
backend/app/tasks/script_tasks.py          # Celery 任务
backend/app/api/v1/scripts.py              # API 路由
backend/app/api/v1/export.py               # 导出功能
backend/app/models/script.py               # 数据模型
backend/app/core/redis_log_publisher.py    # 日志推送
backend/alembic/versions/6646e9d6eb5e_*.py # 数据库迁移
```

### 前端文件
```
frontend/src/pages/user/Workspace/ScriptTab/index.tsx  # 主组件
frontend/src/hooks/useBreakdownLogs.ts                 # WebSocket Hook
frontend/src/components/ConsoleLogger.tsx              # 日志组件
frontend/src/services/api.ts                           # API 调用
```

---

## 十、技术亮点总结

`★ Insight ─────────────────────────────────────`
**架构设计亮点：**

1. **复用基础设施**：剧本生成与剧情拆解共用 WebSocket 和日志系统，减少重复开发

2. **分层日志推送**：任务级、步骤级、流式级三层日志，提供完整的执行可见性

3. **优雅降级**：WebSocket + 轮询双保险，确保在任何网络环境下都能追踪任务状态

4. **类型安全**：前端使用 TypeScript 严格类型检查，后端使用 Pydantic 数据验证

5. **数据完整性**：剧本保存时检查是否已存在，支持更新和创建两种场景

6. **用户体验**：实时日志、进度显示、错误提示，提供流畅的交互体验
`─────────────────────────────────────────────────`

---

## 十一、快速启动指南

### 开发环境
```bash
# 1. 启动后端
cd backend
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# 2. 启动 Celery Worker
celery -A app.core.celery_app worker --loglevel=info

# 3. 启动 Redis
redis-server

# 4. 启动前端
cd frontend
npm run dev
```

### 测试流程
1. 登录系统
2. 进入项目 → Workspace → Script 标签页
3. 选择一个剧集
4. 点击"生成当前集剧本"
5. 观察 ConsoleLogger 实时日志
6. 生成完成后查看剧本内容
7. 测试编辑、审核、导出功能

---

**实施完成时间：** 2026-02-22
**实施人员：** Claude Opus 4.6
**状态：** ✅ 核心功能已完成，待测试验证
