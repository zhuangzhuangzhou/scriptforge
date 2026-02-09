# save-plan 技能示例

## 概述

`/save-plan` 技能用于将 Claude Code 计划模式下的计划文件持久化到项目任务系统。

## 使用场景

1. 在 `/plan` 模式下完成详细计划后
2. 需要跨会话继续执行任务时
3. 需要与团队共享任务计划时

## 基本用法

```bash
# 自动从计划文件提取标题
/save-plan

# 指定任务标题
/save-plan Workspace 重构

# 指定完整标题
/save-plan "API 重构：用户认证模块"
```

## 输出示例

```
✅ 任务已创建
📁 路径: .trellis/tasks/20260208-workspace-refactor/
📋 标题: Workspace 重构
💡 下次继续: 输入 "查看当前任务" 或 "继续执行任务"
```

## 生成的文件结构

```
.trellis/tasks/20260208-{slug}/
├── task.json    # 任务元数据
└── plan.md      # 完整计划内容
```

### task.json 示例

```json
{
  "title": "Workspace.tsx 重构：组件拆分与状态管理优化",
  "slug": "workspace-refactor",
  "status": "pending",
  "created_at": "2026-02-08T12:51:29+08:00",
  "plan_source": "~/.claude/plans/buzzing-growing-tower.md"
}
```

## 工作流程

```
┌─────────────────────────────────────────────────────────────┐
│  1. /plan                                                   │
│     ↓                                                       │
│  2. 制定详细计划（Claude Code 自动保存到 ~/.claude/plans/） │
│     ↓                                                       │
│  3. 退出计划模式                                            │
│     ↓                                                       │
│  4. /save-plan [标题]                                       │
│     ↓                                                       │
│  5. 任务保存到 .trellis/tasks/                              │
│     ↓                                                       │
│  6. 下次会话: "查看当前任务" 继续执行                       │
└─────────────────────────────────────────────────────────────┘
```

## 注意事项

- 如果任务目录已存在，会询问是否覆盖
- 原计划文件不会被删除（保留在 `~/.claude/plans/`）
- 任务状态默认为 `pending`
