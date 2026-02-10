# 通用开发指南

## 开发原则

1. **简洁优先** - 避免过度工程化
2. **一致性** - 遵循现有代码风格
3. **可测试** - 编写可测试的代码
4. **文档化** - 关键逻辑添加注释

## ⚠️ 工作目录规范（重要）

### 核心规则

**所有 AI 编程工作必须在项目根目录执行，严禁切换到子目录**

```bash
# ✅ 正确做法
pwd  # 确认在 /Users/zhouqiang/Data/jim
vim backend/app/main.py
vim frontend/src/App.tsx
./.trellis/scripts/get-context.sh

# ❌ 错误做法
cd backend          # 禁止！
cd frontend         # 禁止！
cd backend/app      # 禁止！
```

### 为什么需要这个规则？

1. **脚本依赖**: `.trellis/scripts/` 中的所有脚本都假设从根目录执行
2. **路径一致性**: 避免相对路径混乱和文件定位错误
3. **防止嵌套**: 曾出现 `backend/backend/` 错误嵌套结构的问题
4. **工作流稳定**: 确保所有自动化工具能正常工作

### 正确的文件操作方式

| 操作 | 正确做法 | 错误做法 |
|------|---------|---------|
| 读取后端文件 | `Read backend/app/main.py` | `cd backend && Read app/main.py` |
| 编辑前端文件 | `Edit frontend/src/App.tsx` | `cd frontend/src && Edit App.tsx` |
| 执行脚本 | `./.trellis/scripts/task.sh` | `cd .trellis && ./scripts/task.sh` |
| 运行测试 | `pytest backend/tests/` | `cd backend && pytest tests/` |

### 历史问题案例

**问题描述**: AI 在工作中频繁使用 `cd` 切换到 `/frontend` 或 `/backend`，导致：
- `.trellis/scripts/` 脚本找不到（相对路径错误）
- 创建了错误的嵌套目录 `backend/backend/`
- 工作流中断，需要手动修复目录结构

**解决方案**: 建立此规范，所有操作使用相对于根目录的路径

## Git 提交规范

```
<type>: <description>

类型:
- feat: 新功能
- fix: 修复
- docs: 文档
- refactor: 重构
- test: 测试
```

## 代码审查清单

- [ ] 代码风格一致
- [ ] 无安全漏洞
- [ ] 错误处理完善
- [ ] 类型定义完整

---

## 重大变更管理 (Breaking Change Protocol)

### 什么是重大变更？

| 类型 | 示例 | 需要审批 |
|------|------|---------|
| 路由重构 | 从 `currentView` 改为 React Router | ✅ 是 |
| 数据库 Schema | 新增/删除表、字段 | ✅ 是 |
| API 契约 | 改变请求/响应结构 | ✅ 是 |
| 前端 UI 大改 | 重新设计页面布局 | ✅ 是 |
| 权限变更 | 修改认证/授权逻辑 | ✅ 是 |
| Bug 修复 | 修复现有功能 | ❌ 否 |
| 小优化 | 性能微调 | ❌ 否 |

### 审批流程

1. **提出变更**: 说明变更内容 + 影响范围
2. **获取同意**: 等待用户明确说 "同意" 或 "可以"
3. **实施变更**: 在分支中实施
4. **验证测试**: 确保功能正常
5. **提 PR 合并**: 走代码审查流程

### 禁止行为

- ❌ 不经同意擅自重构路由
- ❌ 不经同意擅自修改 UI 样式
- ❌ 一次提交混合"功能+重构+样式"
- ❌ 假设代码能工作而不测试

### 为什么需要这个流程？

历史教训：
- 一次路由重构 → 所有子页面乱套
- 一次 UI 优化 → 用户不认可风格
- 一次 API 改动 → 500 错误

**沟通 > 假设**

---

@@@section:skill-save-plan
## 任务管理工作流

### 概述

使用 `/save-plan` 技能将 Claude Code 计划模式下的计划持久化到项目任务系统（`.trellis/tasks/`）。

### 工作流程

```
/plan → 制定计划 → 退出计划模式 → /save-plan → 任务保存 → 下次继续
```

### 使用方法

```bash
# 基本用法（自动提取标题）
/save-plan

# 指定任务标题
/save-plan Workspace 重构
```

### 生成的文件

| 文件 | 用途 |
|------|------|
| `.trellis/tasks/YYYYMMDD-{slug}/task.json` | 任务元数据 |
| `.trellis/tasks/YYYYMMDD-{slug}/plan.md` | 完整计划内容 |
| `.trellis/.current-task` | 当前任务指针 |

### 继续执行任务

下次启动会话后：
- **"查看当前任务"** - 查看任务详情和计划
- **"继续执行任务"** - 开始执行

### 参考示例

详见 `examples/skills/save-plan/README.md`

@@@/section:skill-save-plan
