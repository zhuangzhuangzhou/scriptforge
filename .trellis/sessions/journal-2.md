# 开发会话日志 - Journal 2

记录项目的开发会话历史。

---


## [20260226-112628] Landing 宣传页开发

**时间**: 2026-02-26 11:26:28

**提交**:
- `13eaa0f` - feat: 添加 Landing 宣传页


## 完成内容

新增官网宣传页 Landing.tsx，展示产品核心功能和工作流程。

| 模块 | 说明 |
|------|------|
| Hero Section | 打字机动画标题 + 工作流演示 |
| 功能展示 | 6 大核心功能卡片 |
| 工作流程 | 四步流程图解 |
| Agent 系统 | 多 Agent 协作介绍 |
| CTA | 注册引导 |

**UI 风格统一**:
- 复用 AnimatedBackground 动态背景
- 统一 Logo 图标为 Film
- 边角装饰与登录页一致
- 版本号统一为 v1.0.0

**路由配置**:
- 未登录用户访问 `/` 显示 Landing
- 已登录用户自动跳转 `/dashboard`

**修改文件**:
- `frontend/src/pages/Landing.tsx` (新增)
- `frontend/src/App.tsx`
- `frontend/src/pages/auth/Login.tsx`
- `frontend/src/pages/user/Dashboard.tsx`

---


## [20260226-113539] 通知公告和兑换码系统实现

**时间**: 2026-02-26 11:35:39

**提交**:
- `ddea721` - feat: 通知公告系统
- `ac8aa6d` - feat: 兑换码系统
- `6406d87` - feat: 剧本章节功能增强
- `82e96c7` - refactor: 代码优化和布尔值比较修复
- `12d7959` - docs: 更新开发规范文档
- `5bad3e5` - chore: 更新会话记录


## 功能实现

| 功能模块 | 描述 |
|---------|------|
| **通知公告系统** | 完整的通知公告功能，支持管理端发布和用户端查看 |
| **兑换码系统** | 兑换码管理和使用功能，支持积分充值和会员升级 |
| **剧本章节增强** | 支持章节级别的剧本生成和管理 |
| **代码质量优化** | SQLAlchemy 布尔值比较规范化 |
| **规范文档更新** | 记录新学到的模式和最佳实践 |

## 通知公告系统详情

### 后端实现
- **数据库模型**：
  - `Announcement`：通知表（标题、内容、优先级、类型、发布状态、过期时间）
  - `AnnouncementRead`：已读记录表（防重复标记）
- **数据库迁移**：`5420f22114d0_add_announcements_tables.py`
- **API 端点**（12 个）：
  - 管理端 8 个：CRUD、发布/取消发布、统计信息
  - 用户端 4 个：列表查询、详情、标记已读、未读数量
- **通知服务**：`NotificationService` 支持系统自动通知（异步/同步版本）
- **关键修复**：FastAPI 路由顺序（`/announcements/unread-count` 必须在 `/{announcement_id}` 之前）

### 前端实现
- **管理端**：`pages/admin/Announcements/`
  - 主页面：列表、筛选、搜索、分页
  - 创建/编辑模态框：支持 Markdown 内容
  - 统计信息模态框：显示已读人数、已读率
- **用户端**：`components/NotificationBell.tsx`
  - 铃铛图标（Bell from lucide-react）
  - 未读数量徽章（红点）
  - 下拉通知列表
- **UI 组件标准化**：全部使用 Glass 组件
  - GlassTable、GlassModal、GlassInput、GlassSelect、GlassDatePicker
  - GlassInput 增强：添加 Search 和 TextArea 子组件（Object.assign 模式）

### 技术要点
1. **FastAPI 路由顺序**：具体路由必须在参数路由之前定义
2. **SQLAlchemy 布尔值比较**：使用 `.is_(True/False)` 而非 `== True/False`
3. **React 子组件导出**：使用 `Object.assign` 模式添加子组件
4. **已读状态查询**：LEFT JOIN 优化查询性能
5. **防重复标记**：`INSERT ON CONFLICT DO NOTHING`

## 兑换码系统详情

### 后端实现
- **数据库模型**：`RedeemCode`（兑换码、类型、金额、使用状态、过期时间）
- **数据库迁移**：`20260226_add_redeem_codes.py`
- **API 端点**：
  - 管理端：创建、列表、删除兑换码
  - 用户端：兑换码使用（支持积分充值和会员升级）

### 前端实现
- **管理端**：`pages/admin/RedeemCodes/index.tsx`
  - 兑换码管理页面（创建、列表、删除）
- **用户端**：`components/modals/RedeemCodeModal.tsx`
  - 兑换码输入弹窗
- **常量提取**：`constants/tier.ts`
  - `TIER_NAMES`：用户等级名称映射
  - `TIER_COLORS`：用户等级颜色映射
  - 避免在多个文件中重复定义

### 组件优化
- `BillingModal`：使用共享常量
- `RechargeModal`：使用共享常量
- `TierComparisonModal`：使用共享常量

## 剧本章节功能增强

### 后端实现
- **数据库迁移**：添加 `scripted_chapters` 字段到 `projects` 表
- **项目模型**：新增 `scripted_chapters` 字段（已生成剧本的章节列表）
- **API 增强**：
  - `/projects/{id}` 返回 `scripted_chapters`
  - `/scripts` 端点支持章节级别的剧本生成
- **任务状态**：新增 `SCRIPT_GENERATING` 状态
- **Celery 任务**：`script_tasks` 支持章节级别生成

### 前端实现
- **ScriptTab**：支持章节级别的剧本生成和管理
- **EpisodeList**：显示章节列表和生成状态
- **useScriptPolling**：轮询章节生成状态
- **useScriptQueue**：管理章节生成队列

## 代码质量优化

### 后端优化
- **布尔值比较修复**：
  - `breakdown.py`：`.is_(False)` 替代 `== False`
  - `websocket.py`：布尔值比较优化
  - `breakdown_tasks.py`：任务逻辑优化
- **避免 E712 flake8 警告**

### 前端优化
- `QuotaLimitModal`：组件优化
- `GlassDatePicker`：样式和功能优化
- `mockData.ts`：测试数据更新

## 规范文档更新

### 后端规范（`.trellis/spec/backend/index.md`）
- **新增 8.3 节**：SQLAlchemy 布尔值比较规范
  - 使用 `.is_(True/False)` 替代 `== True/False`
  - 避免 E712 flake8 警告
- **新增 8.11 节**：FastAPI 路由顺序错误
  - 具体路由必须在参数路由之前定义
  - 详细示例和错误说明

### 前端规范（`.trellis/spec/frontend/ui-consistency.md`）
- **表格序号列**：改为可选（根据实际需求决定）
- **GlassSelect 使用方法**：`options` 属性 vs `Option` 子组件
- **GlassInput 子组件支持**：Object.assign 实现模式
- **组件使用表**：列出所有 Glass 组件及其使用场景

## 关键文件清单

### 新增文件（14 个）
**后端**：
- `backend/app/models/announcement.py`
- `backend/app/models/redeem_code.py`
- `backend//announcements.py`
- `backend/app/api/v1/redeem.py`
- `backend/app/services/notification_service.py`
- `backend/alembic/versions/5420f22114d0_add_announcements_tables.py`
- `backend/alembic/versions/20260226_add_redeem_codes.py`
- `backend/alembic/versions/20260226_add_scripted_chapters.py`

**前端**：
- `frontend/src/components/NotificationBell.tsx`
- `frontend/src/components/modals/RedeemCodeModal.tsx`
- `frontend/src/constants/tier.ts`
- `frontend/src/pages/admin/Announcements/index.tsx`
- `frontend/src/pages/admin/Announcements/AnnouncementModal.tsx`
- `frontend/src/pages/admin/Announcements/AnnouncementStats.tsx`
- `frontend/src/pages/admin/RedeemCodes/index.tsx`

### 修改文件（31 个）
**后端**：
- `backend/app/models/__init__.py`
- `backend/app/models/project.py`
- `backend/app/api/v1/router.py`
- `backend/app/api/v1/admin_core.py`
- `backend/app/api/v1/breakdown.py`
- `backend/app/api/v1/projects.py`
- `backend/app/api/v1/scripts.py`
- `backend/app/api/v1/websocket.py`
- `backend/app/core/status.py`
- `backend/app/tasks/breakdown_tasks.py`
- `backend/app/tasks/script_tasks.py`

**前端**：
- `frontend/src/components/MainLayout.tsx`
- `frontend/src/components/ui/GlassInput.tsx`
- `frontend/src/components/ui/GlassDatePicker.tsx`
- `frontend/src/components/modals/BillingModal.tsx`
- `frontend/src/components/modals/RechargeModal.tsx`
- `frontend/src/components/modals/QuotaLimitModal.tsx`
- `frontend/src/components/modals/TierComparisonModal.tsx`
- `frontend/src/context/AuthContext.tsx`
- `frontend/src/pages/admin/Dashboard.tsx`
- `frontend/src/pages/user/Workspace/ScriptTab/index.tsx`
- `frontend/src/pages/user/Workspace/ScriptTab/EpisodeList.tsx`
- `frontend/src/pages/user/Workspace/ScriptTab/hooks/useScriptPolling.ts`
- `frontend/src/pages/user/Workspace/ScriptTab/hooks/useScriptQueue.ts`
- `frontend/src/services/api.ts`
- `frontend/src/services/mockData.ts`

**规范文档**：
- `.trellis/spec/backend/index.md`
- `.trellis/spec/frontend/index.md`
- `.trellis/spec/frontend/ui-consistency.md`

**会话记录**：
- `.trellis/sessions/index.md`
- `.trellis/sessions/journal-1.md`
- `.trellis/sessions/journal-2.md`（新建）

## 问题解决记录

### 问题 1：UUID 解析错误
**症状**：访问 `/announcements/unread-count` 时报错 `"Input should be a valid UUID, invalid character: expected an optional prefix of 'urn:uuid:' followed by [0-9a-fA-F-], found 'u' at 1"`

**原因**：FastAPI 路由定义顺序错误，`/announcements/{announcement_id}` 在 `/announcements/unread-count` 之前，导致 "unread-count" 被当作 UUID 参数解析

**解决方案**：将 `/announcements/unread-count` 路由定义移到 `/announcements/{announcement_id}` 之前

**规范更新**：在 `.trellis/spec/backend/index.md` 新增 8.11 节记录此模式

### 问题 2：管理端通知页面空白
**症状**：点击管理端通知公告页面后显示空白

**原因**：`const { Search } = GlassInput;` 失败，因为 `GlassInput` 没有导出 `Search` 子组件

**解决方案**：使用 `Object.assign` 模式为 `GlassInput` 添加 `Search` 和 `TextArea` 子组件

**规范更新**：在 `.trellis/spec/frontend/ui-consistency.md` 新增 GlassInput 子组件支持模式

### 问题 3：通知图标样式被改变
**症状**：用户端导航栏通知图标样式与原设计不符

**原因**：使用了 Ant Design 的 `BellOutlined` 图标，样式不一致

**解决方案**：恢复使用 lucide-react 的 `Bell` 图标，恢复原始按钮样式（`h-10 px-3 bg-slate-900/50` 等）

### 问题 4：组件未使用 Glass 变体
**症状**：`AnnouncementModal` 和 `AnnouncementStats` 使用原生 Ant Design 组件

**原因**：初始实现时未遵循项目规范

**解决方案**：
- 替换所有 Ant Design 组件为 Glass 变体
- `Modal` → `GlassModal`
- `Input` → `GlassInput`
- `Select` → `GlassSelect`（使用 `options` 属性而非 `Option` 子组件）
- `DatePicker` → `GlassDatePicker`

**规范更新**：在 `.trellis/spec/frontend/ui-consistency.md` 强调必须使用项目定义的 Glass 组件

## 代码统计

- **新增代码**：+1550 行
- **删除代码**：-404 行
- **净增加**：+1146 行
- **新增文件**：14 个
- **修改文件**：31 个
- **提交数量**：6 个

## 技术亮点

1. **完整的通知系统架构**：从数据库模型到前端 UI 的完整实现
2. **系统自动通知支持**：为未来的任务完成、积分不足等场景预留接口
3. **代码复用优化**：提取共享常量到 `constants/tier.ts`
4. **UI 组件标准化**：确保所有组件使用 Glass 变体
5. **规范文档同步更新**：将实现过程中学到的模式记录到规范文档

## 后续建议

1. **测试通知推送**：测试管理员发布通知后用户端是否能正常接收
2. **测试兑换码功能**：测试兑换码创建、使用、过期等场景
3. **测试章节生成**：测试章节级别的剧本生成 **考虑 WebSocket 推送**：未来可以将通知轮询改为 WebSocket 实时推送
5. **系统自动通知集成**：在任务完成、积分不足等场景集成自动通知

---


## [20260226-124920] Script Tab 优化 - 无限滚动和单集刷新

**时间**: 2026-02-26 12:49:20

**提交**:
- `c0e3af1` - feat: Script Tab 优化 - 无限滚动和单集刷新


## 主要改动

| 模块 | 改动内容 |
|------|---------|
| 后端 API | `episodes/summary` 接口优化，只查询必要字段，减少数据库 IO |
| 前端列表 | 分页改为无限滚动，提升大数据量场景下的用户体验 |
| 数据刷新 | 任务完成后只刷新单集数据，保持用户当前浏览位置 |
| UI 样式 | EpisodeCard 统一高度 72px，显示剧集标题和状态信息 |
| 规范文档 | 添加"单条数据刷新"模式到前端性能优化规范 |

## 技术要点

- 后端使用 `select()` 指定字段查询，避免加载整个 ORM 对象
- 布尔比较改为 `.is_(True)` 符合 SQLAlchemy 规范
- 前端 `refreshEpisode()` 函数实现单集数据刷新，不影响分页状态
- 无限滚动使用 `onScroll` 检测距离底部 100px 时触发加载

## 修改文件

- `backend/app/api/v1/scripts.py` - API 查询优化
- `frontend/src/pages/user/Workspace/ScriptTab/index.tsx` - 无限滚动和单集刷新
- `frontend/src/pages/user/Workspace/ScriptTab/EpisodeList.tsx` - 无限滚动组件
- `frontend/src/pages/user/Workspace/ScriptTab/EpisodeCard.tsx` - 卡片样式统一
- `.trellis/spec/frontend/performance-optimization.md` - 规范更新

---


## [20260226-125024] Admin 用户管理页面增强

**时间**: 2026-02-26 12:50:24

**提交**:
- `4ffb07d` - feat: Admin 用户管理页面增加登录信息显示


| 改动 | 说明 |
|------|------|
| UserManagement 登录信息 | 添加注册时间和最近登录列，使用相对时间显示 |
| GlassCard 增强 | 添加 onClick prop 支持点击事件 |
| 前端规范更新 | 新增 Tailwind 动态类名处理模式 |

**修改文件**:
- `frontend/src/pages/admin/UserManagement.tsx` - 添加时间列
- `frontend/src/components/ui/GlassCard.tsx` - onClick 支持
- `.trellis/spec/frontend/ui-consistency.md` - 规范更新

---


## [20260226-125043] 用户反馈功能实现

**时间**: 2026-02-26 12:50:43

**提交**:
- `95fac24` - feat: 用户反馈功能
- `db116f1` - docs: 新增异步错误类型处理规范


## 完成内容

实现完整的用户反馈系统，支持用户提交需求建议、问题报告，管理员可在后台查看和处理。

### 后端
- 新增 `Feedback` 模型和数据库迁移
- 用户提交反馈 API (`POST /feedback`)
- 管理端反馈列表/详情/更新 API

### 前端
- Header 添加反馈按钮入口 (MessageSquare 图标)
- `FeedbackModal` 反馈弹窗组件
- 管理端反馈管理页面 (`/admin/feedbacks`)
- Dashboard 添加反馈管理卡片入口

### 规范更新
- `react-hooks-patterns.md` 新增异步错误类型处理规范

**关键文件**:
- `backend/app/models/feedback.py`
- `backend/app/api/v1/feedback.py`
- `frontend/src/components/modals/FeedbackModal.tsx`
- `frontend/src/pages/admin/Feedbacks/index.tsx`

---


## [20260226-150212] 修复任务取消状态和会话混用问题

**时间**: 2026-02-26 15:02:12

**提交**:
- `8204d1b` - fix: 修复任务取消状态和会话混用问题



## 问题背景

用户报告任务取消后状态停留在 `cancelling`，导致：
- `/batch/{batch_id}/current-task` 接口仍返回已取消的任务
- 新任务无法启动
- 前端显示异常

## 根本原因分析

1. **状态转换不完整**
   - API 端设置 `CANCELLING` 状态
   - 依赖 Celery 回调更新为 `CANCELED`
   - `revoke(terminate=True)` 强制终止进程，回调无法执行

2. **会话混用问题**
   - 异步会话查询 `batch` 对象
   - 创建同步会话检查历史记录
   - 根据同步会话结果修改异步会话对象
   - 导致数据不一致和 ORM 状态问题

## 解决方案

### 1. 状态管理简化
```python
# 修改前：两步转换
task.status = TaskStatus.CANCELLING  # 中间状态
# ... 等待 Celery 回调 ...
task.status = TaskStatus.CANCELED    # 最终状态

# 修改后：直接设置最终状态
task.status = TaskStatus.CANCELED    # 一步到位
task.current_step = "已取消"
```

### 2. 会话管理优化
```python
# 修改前：会话混用
check_db = SyncSessionLocal()  # 创建同步会话
has_success = _check_previous_breakdown_success(check_db, ...)
check_db.close()
batch.breakdown_status = ...  # 修改异步会话对象

# 修改后：单一异步会话
async def _check_previous_breakdown_success_async(
    db: AsyncSession,  # 使用同一个异步会话
    batch_id: str,
    current_task_id: str
) -> bool:
    # 所有查询在同一会话中完成
    ...

has_success = await _check_previous_breakdown_success_async(db, ...)
```

### 3. 积分处理完整
- **主任务**：根据状态和 Token 消耗正确处理
  - `RUNNING` 且 Token>0 → 扣除 Token 费用
  - `RUNNING` 且 Token=0 → 返还配额
  - `QUEUED` → 返还配额
- **后续任务**：批量返还配额
- **防重复扣费**：添加 `api_handled_credits` 标记

## 技术亮点

| 改进项 | 修改前 | 修改后 |
|--------|--------|--------|
| **会话管理** | 异步+同步混用 | 单一异步会话 |
| **状态转换** | 两步（CANCELLING→CANCELED） | 一步（直接CANCELED） |
| **积分处理** | 只处理主任务 | 主任务+后续任务 |
| **代码行数** | 2,506 行 | 新增 60 行辅助函数 |

## 修改文件

**核心修改**：
- `backend/app/api/v1/breakdown.py`
  - 新增 `_check_previous_breakdown_success_async()` 函数（60行）
  - 修复 `stop_breakdown_task()` 接口逻辑
  - 移除未使用的 `AsyncSessionLocal` 导入

**规范更新**：
- `.trellis/spec/backend/index.md`
  - 新增 8.12 节：异步/同步会话混用问题
  - 包含完整的错误示例、正确做法和预防措施

## 代码统计

- **新增**：279 行
- **删除**：89 行
- **净增加**：190 行

## 测试验证

手动修复了卡在 `cancelling` 状态的任务：
```bash
任务 ID: f9d41419-b6fd-4ccb-9a7d-b3c5560efb7d
修复前: status=cancelling, current_step="正在停止"
修复后: status=canceled, current_step="已取消"
批次状态: pending（智能回滚检查后）
```

## 知识沉淀

在规范文档中记录了：
1. **问题定义**：会话混用的场景和症状
2. **根本原因**：ORM 对象绑定、事务隔离、跨会话修改
3. **解决方案**：创建异步版本、单一会话原则
4. **预防措施**：4 条具体建议
5. **相关错误**：链接到 8.6、8.7 节

## 影响范围

- ✅ 后端 API 层（停止任务接口）
- ✅ 无前端修改（接口契约未变）
- ✅ 无数据库 schema 变更
- ✅ 向后兼容

---


## [20260226-213208] 修复 Token 计费不匹配问题

**时间**: 2026-02-26 21:32:08

**提交**:
- `925b2b9` - fix: 修复 LLM adapter 流式响应中 Token 统计缺失问题


## 问题诊断

1. **后台任务检查**：Celery 任务正常运行，无卡住
2. **Token 计费分析**：
   - 发现 MiniMax-M2.1 模型定价为 4000 积分/1K（默认值 2 积分/1K 的 2000 倍）
   - LLMCallLog 中 prompt_tokens 和 response_tokens 为 None
   - 计费系统降级到文本长度估算，导致计费不准确

## 修复内容

| 文件 | 修改 |
|------|------|
| anthropic_adapter.py | 添加流式响应 token 提取逻辑 |
| openai_adapter.py | 添加 stream_options={"include_usage": True} 和 token 提取 |
| gemini_adapter.py | 添加完整的日志记录和 token 提取 |
| llm-token-tracking.md | 新增规范文档 |

## 技术细节

- Anthropic: 监听 message_start 和 message_delta 事件
- OpenAI: 使用 stream_options 参数在最后返回 usage
- Gemini: 从每个 chunk 的 usageMetadata 提取

## 待验证

- [ ] 重启 Celery Worker
- [ ] 创建测试任务验证 token 字段正确记录

---

