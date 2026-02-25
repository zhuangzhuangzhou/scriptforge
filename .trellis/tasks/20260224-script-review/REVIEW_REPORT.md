# Script 页面代码审查报告

**审查日期**: 2026-02-24
**审查范围**: 前端 + 后端 + 类型定义

---

## 一、审查概览

| 审查维度 | 前端 | 后端 | 类型定义 |
|----------|------|------|----------|
| 功能完整性 | 60% | 80% | 70% |
| 代码质量 | 65% | 80% | 60% |
| 性能 | 70% | N/A | N/A |
| 类型安全 | 70% | 80% | 50% |

---

## 二、高优先级问题汇总

### 2.1 前端问题

| # | 文件 | 问题描述 | 影响 |
|---|------|----------|------|
| 1 | ScriptGeneration.tsx | `loadScripts` 函数为空，未实现 | 剧本列表无法加载 |
| 2 | ScriptGeneration.tsx | 自动生成按钮无 onClick 处理器 | 无法触发生成 |
| 3 | ScriptTab/index.tsx | 状态管理不一致，ref 和 state 混用 | 可能导致逻辑错误 |
| 4 | ScriptTab/index.tsx | 第 678 行 Tailwind 样式笔误 | UI 显示问题 |
| 5 | ScriptTab/index.tsx | 组件 1120 行，体积过大 | 维护困难 |

### 2.2 后端问题

| # | 文件 | 问题描述 | 影响 |
|---|------|----------|------|
| 1 | scripts.py | 路由顺序可能导致路径冲突 | API 匹配异常 |
| 2 | scripts.py | 批量积分预扣无事务处理 | 数据不一致风险 |
| 3 | scripts.py | 积分预扣后任务启动失败无回滚 | 用户积分损失 |
| 4 | script.py | content 字段 NOT NULL 但可能为 None | 数据库写入异常 |

### 2.3 类型定义问题

| # | 文件 | 问题描述 | 影响 |
|---|------|----------|------|
| 1 | types.ts | 剧本状态与后端不匹配 | 状态显示错误 |
| 2 | types.ts | QA 状态大小写不一致 | 质检状态异常 |
| 3 | types.ts | EpisodeScript 缺少关键字段 | 数据不完整 |

---

## 三、详细问题清单

### 3.1 前端 - ScriptGeneration.tsx (高优先级)

```typescript
// 问题 1: loadScripts 未实现
const loadScripts = async () => {
  // TODO: 实现数据加载
};

// 问题 2: 按钮无事件处理
<Button type="dashed" block icon={<RobotOutlined />}>
  自动生成下一集
</Button>
```

### 3.2 前端 - ScriptTab/index.tsx (高优先级)

```typescript
// 问题 3: 状态管理不一致
const selectedEpisodeRef = useRef<string | null>(null);
const [selectedEpisode, setSelectedEpisode] = useState<string | null>(null);
// 两个状态可能不同步

// 问题 4: 样式笔误 (第 678 行)
className="bg-slate-700:bg-slate-"  // 应该是 bg-slate-700:hover:bg-slate-
```

### 3.3 后端 - scripts.py (高优先级)

```python
# 问题 1: 路由顺序
# 当前: /scripts/{script_id} 在 /scripts/episode/start 之前
# 风险: /scripts/episode/start 可能被 /scripts/{script_id} 拦截

# 问题 2: 批量积分预扣无事务
for _ in range(required):
    consume_result = await quota_service.consume_credits(...)
    # 如果中途失败，前面的积分已扣但任务未创建
```

### 3.4 类型定义 - types.ts (高优先级)

```typescript
// 问题 1: 状态不匹配
// 前端
status?: 'pending' | 'generating' | 'completed' | 'failed' | 'approved';
// 后端实际
status?: 'draft' | 'approved';

// 问题 2: QA 状态大小写
// 前端
qa_status?: 'pending' | 'PASS' | 'FAIL';
// 后端实际
qa_status?: 'pending' | 'pass' | 'fail';
```

---

## 四、代码亮点

### 前端
1. 良好的错误处理统一机制
2. 骨架屏加载状态完善
3. 未保存更改提示用户体验好

### 后端
1. 任务进度追踪机制完善
2. Celery 重试配置合理
3. 积分策略设计清晰
4. Redis 日志发布优雅降级

### 类型定义
1. PlotPoint 类型设计清晰
2. ScriptStructure 四段式结构合理

---

## 五、修复建议优先级

### 立即修复 (今天)

| 任务 | 预计工作量 |
|------|------------|
| 修复 ScriptGeneration.tsx 的 loadScripts 实现 | 30 分钟 |
| 修复类型定义中的状态不匹配 | 15 分钟 |
| 修复 Tailwind 样式笔误 | 5 分钟 |

### 本周内修复

| 任务 | 预计工作量 |
|------|------------|
| 后端路由顺序调整 | 15 分钟 |
| 批量积分事务处理 | 1 小时 |
| ScriptTab 组件拆分 | 2 小时 |

### 长期优化

| 任务 | 预计工作量 |
|------|------------|
| 移除 any 类型，使用具体接口 | 2 小时 |
| 添加任务取消 API | 1 小时 |
| 列表虚拟滚动 | 1 小时 |

---

## 六、相关文件清单

### 前端
- `frontend/src/pages/user/ScriptGeneration.tsx`
- `frontend/src/pages/user/Workspace/ScriptTab/index.tsx`
- `frontend/src/types.ts`
- `frontend/src/services/api.ts`

### 后端
- `backend/app/api/v1/scripts.py`
- `backend/app/models/script.py`
- `backend/app/tasks/script_tasks.py`
