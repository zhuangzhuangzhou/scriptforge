# Breakdown 系统架构说明

本文档说明 `init_simple_system.py` 与 `breakdown_tasks.py` 的关系，以及 `BUILTIN_AGENTS` 与 `SimpleAgentExecutor` 的区别。

---

## 一、核心文件关系

```
┌─────────────────────────────────────────────────────────────┐
│                      init_simple_system.py                   │
│         （配置中心 - 定义 Skills 和 Agents）                 │
├─────────────────────────────────────────────────────────────┤
│  BUILTIN_SKILLS:                                            │
│    - webtoon_breakdown (剧情拆解)                           │
│    - breakdown_aligner (质检)                               │
│    - webtoon_breakdown_repair (修复)                       │
│    - webtoon_script (剧本创作)                              │
│    - webtoon_aligner (剧本质检)                             │
├─────────────────────────────────────────────────────────────┤
│  BUILTIN_AGENTS:                                            │
│    - breakdown_agent (剧情拆解 Agent)                       │
│    - script_agent (剧本创作 Agent)                          │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                      breakdown_tasks.py                      │
│              （执行层 - 任务入口和调用逻辑）                 │
├─────────────────────────────────────────────────────────────┤
│  - _execute_breakdown_sync()                                │
│  - _handle_task_cancelled_sync()                            │
│  - 主备切换逻辑 (Agent → Skill fallback)                    │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                      SimpleAgentExecutor                     │
│              （执行引擎 - 通用工作流执行器）                  │
├─────────────────────────────────────────────────────────────┤
│  - execute_agent()                                          │
│  - 读取 workflow 配置                                       │
│  - 按步骤执行 Skills                                         │
│  - 条件判断和循环控制                                        │
│  - 错误处理和重试                                            │
└─────────────────────────────────────────────────────────────┘
```

---

## 二、BUILTIN_AGENTS vs SimpleAgentExecutor

### 2.1 区别对比

| | BUILTIN_AGENTS | SimpleAgentExecutor |
|--|----------------|--------------------|
| **类型** | 配置/计划（JSON） | 执行代码（Python） |
| **位置** | `init_simple_system.py:435-544` | `simple_executor.py` |
| **作用** | 描述"做什么" | 真正"去执行" |
| **修改频率** | 经常改动 | 基本不动 |

### 2.2 形象比喻

**BUILTIN_AGENTS = 菜谱**
```json
{
  "type": "loop",
  "max_iterations": 3,
  "steps": [
    {"id": "breakdown", "skill": "webtoon_breakdown", ...},
    {"id": "qa", "skill": "breakdown_aligner", ...}
  ]
}
```
- 写清楚：先放什么，后放什么
- 什么时候出锅（退出条件）
- 最多炒几次（max_iterations）

**SimpleAgentExecutor = 锅和铲子**
```python
class SimpleAgentExecutor:
    async def execute_agent(self, agent_name, context, task_id):
        # 按菜谱一步步操作
        # 控制火候（条件判断）
        # 决定什么时候出锅（退出循环）
```
- 不管菜谱内容是什么
- 只管按菜谱执行
- 处理各种异常情况

---

## 三、breakdown_agent 工作流详解

### 3.1 定义位置

`init_simple_system.py:436-504`

### 3.2 工作流结构

```python
"breakdown_agent": {
    "display_name": "剧情拆解 Agent",
    "description": "智能剧情拆解：拆解 → 质检 → 自动修正循环，直到质量达标",
    "category": "breakdown",
    "workflow": {
        "type": "loop",                           # 循环类型
        "max_iterations": 3,                      # 最多循环3次
        "exit_condition": "qa_result.status == 'PASS' or qa_result.score >= 70",
        "steps": [
            # 第1步：拆解
            {
                "id": "breakdown",
                "skill": "webtoon_breakdown",
                "inputs": {...},
                "output_key": "plot_points",
                "on_fail": "stop",
                "max_retries": 1
            },
            # 第2步：质检
            {
                "id": "qa",
                "skill": "breakdown_aligner",
                "inputs": {...},
                "output_key": "qa_result",
                "on_fail": "skip",
                "max_retries": 0
            },
            # 第3步：修复（质检不通过才执行）
            {
                "id": "breakdown_retry",
                "skill": "webtoon_breakdown_repair",
                "condition": "qa_result.status != 'PASS' and qa_result.score < 70 and (qa_result.issues or qa_result.fix_instructions)",
                "inputs": {...},
                "output_key": "plot_points",
                "on_fail": "skip",
                "max_retries": 0
            },
            # 第4步：再次质检
            {
                "id": "qa_retry",
                "skill": "breakdown_aligner",
                "condition": "qa_result.status != 'PASS' and qa_result.score < 70",
                "inputs": {...},
                "output_key": "qa_result",
                "on_fail": "skip",
                "max_retries": 0
            }
        ]
    }
}
```

### 3.3 执行流程

```
┌─────────────────────────────────────────────────────────────────┐
│                    breakdown_agent 执行流程                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  start                                                          │
│    │                                                           │
│    ▼                                                           │
│  ┌─────────────────────┐                                       │
│  │  1. webtoon_breakdown │  ← 拆解小说原文，生成剧情点        │
│  │         (Skill)        │                                       │
│  └─────────────────────┘                                       │
│    │                                                           │
│    │ plot_points                                                │
│    ▼                                                           │
│  ┌─────────────────────┐                                       │
│  │  2. breakdown_aligner │  ← 质检拆解结果                     │
│  │         (Skill)        │                                       │
│  └─────────────────────┘                                       │
│    │                                                           │
│    │ qa_result                                                 │
│    ▼                                                           │
│  ┌─────────────────────────────────────────────────┐          │
│  │           质检通过 or 分数 >= 70 ?               │          │
│  │           (退出条件判断)                          │          │
│  └─────────────────────────────────────────────────┘          │
│       │                    │                                 │
│      YES                  NO                                  │
│       │                    │                                 │
│       ▼                    ▼                                 │
│   ┌──────┐          ┌─────────────────────┐                  │
│   │ 结束  │          │ 3. webtoon_breakdown_repair           │
│   └──────┘          │        (Skill)        │                  │
│                     └─────────────────────┘                  │
│                       │                                        │
│                       │ plot_points (修复后)                  │
│                       ▼                                        │
│                     ┌─────────────────────┐                  │
│                     │ 4. breakdown_aligner │  ← 再次质检     │
│                     │        (Skill)        │                  │
│                     └─────────────────────┘                  │
│                       │                                        │
│                       └──────────┬─────────────┐              │
│                                  │             │               │
│                         循环次数 < 3 ?   循环次数 >= 3        │
│                                  │             │               │
│                                  ▼             ▼              │
│                              继续循环      强制退出           │
└─────────────────────────────────────────────────────────────────┘
```

---

## 四、修改指南

### 4.1 常见修改场景

| 改动需求 | 修改位置 | 示例 |
|---------|---------|------|
| 增删工作流步骤 | `BUILTIN_AGENTS` | 增加"人工审核"步骤 |
| 修改循环次数 | `BUILTIN_AGENTS` | `max_iterations: 3 → 5` |
| 修改退出条件 | `BUILTIN_AGENTS` | `score >= 70 → 80` |
| 修改质检规则 | `BUILTIN_SKILLS` | `breakdown_aligner.prompt_template` |
| 修改修复逻辑 | `BUILTIN_SKILLS` | `webtoon_breakdown_repair.prompt_template` |
| 新增执行模式 | `SimpleAgentExecutor` | 新增 parallel 类型 |

### 4.2 只改 BUILTIN_AGENTS 的场景

✅ **增加步骤**
```python
{
    "id": "manual_review",
    "skill": "manual_review_skill",
    "condition": "task.priority == 'high'",
    ...
}
```

✅ **修改条件**
```python
"condition": "qa_result.status != 'PASS' and qa_result.score < 70"
```

✅ **调整阈值**
```python
"exit_condition": "qa_result.status == 'PASS' or qa_result.score >= 80"
```

### 4.3 必须改 SimpleAgentExecutor 的场景

⚠️ **新增 workflow 类型**
```python
"type": "parallel"  # 目前只支持 "loop"
```

⚠️ **新增 condition 语法**
```python
"condition": "qa_result.score < 70 and task.priority == 'high'"
# 如果当前引擎不支持解析这种语法
```

⚠️ **新增 on_fail 策略**
```python
"on_fail": "retry_with_different_model"  # 目前只支持 "stop"、"skip"
```

---

## 五、主备切换机制

### 5.1 执行路径

`breakdown_tasks.py` 中的主备切换逻辑：

```python
# ============================================================
# 主备切换机制：优先用 Agent 执行，失败则回退到直接调用 Skill
#
# Agent 模式：执行 breakdown_agent 工作流，内部包含：
#   1. webtoon_breakdown (拆解)
#   2. breakdown_aligner (质检)
#   3. webtoon_breakdown_repair (修复，条件执行)
#   4. 循环直到质检通过或达到最大次数
#
# Skill 模式（回退）：直接调用单个 Skill，外部补充质检
# ============================================================
```

### 5.2 流程图

```
┌─────────────────────────────────────────────────────────────────┐
│                    主备切换执行流程                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  _execute_breakdown_sync()                                      │
│    │                                                           │
│    │ use_agent = True?                                         │
│    ▼                                                           │
│  ┌─────────────────────┐                                       │
│  │    尝试 Agent 执行    │  ← SimpleAgentExecutor              │
│  │  execute_agent()     │     breakdown_agent                  │
│  └─────────────────────┘                                       │
│         │                                                      │
│         │ 成功 + 有结果                                         │
│         ▼                                                      │
│  ┌──────────────┐                                              │
│  │  返回结果 ✓   │                                              │
│  └──────────────┘                                              │
│         │                                                      │
│    ┌────┴────┐                                                  │
│    │         │                                                  │
│   失败      没结果                                              │
│    │         │                                                  │
│    ▼         ▼                                                  │
│  ┌─────────────────────┐                                       │
│  │   回退到 Skill 执行   │  ← 直接调用 Skill                    │
│  │  used_skill_fallback │     外部补充质检和修复                 │
│  └─────────────────────┘                                       │
│         │                                                      │
│         ▼                                                      │
│  ┌─────────────────────────────────────────────────┐          │
│  │  auto_fix_enabled = use_agent and not used_skill_fallback │ │
│  │  (Agent模式禁用外部自动修正，回退模式启用)          │          │
│  └─────────────────────────────────────────────────┘          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 六、相关文件索引

| 文件路径 | 说明 |
|---------|------|
| `app/core/init_simple_system.py` | Skills 和 Agents 配置定义 |
| `app/tasks/breakdown_tasks.py` | 拆解任务入口和执行逻辑 |
| `app/ai/simple_executor.py` | SimpleAgentExecutor 实现 |
| `app/models/skill.py` | Skill 数据模型 |
| `app/models/agent.py` | SimpleAgent 数据模型 |
| `app/api/v1/breakdown.py` | 拆解 API 端点 |

---

## 七、常见问题

### Q1: 修改了 BUILTIN_AGENTS，为什么没生效？
确保应用重启了。`init_simple_system.py` 在启动时加载配置到数据库，修改后需要重启服务。

### Q2: 质检不通过，但是没有触发修复流程？
检查 `condition` 字段：
```python
"condition": "qa_result.status != 'PASS' and qa_result.score < 70 and (qa_result.issues or qa_result.fix_instructions)"
```
需要同时满足：状态不通过 + 分数不够 + 有具体的修复建议。

### Q3: 循环次数到了，但是质检还没通过会怎样？
强制退出循环，返回当前结果。实际拆解数据会保存，但 `qa_status` 仍为 "pending" 或失败状态。

---

*文档更新时间: 2026-02-15*
