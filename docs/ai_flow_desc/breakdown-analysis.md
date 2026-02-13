# 剧集拆解(Plot Breakdown)系统分析

> 分析日期：2026-02-12

## 一、整体流程

```
用户点击"开始拆解"
  → 前端调用 API
  → 后端创建 AITask + 启动 Celery 任务
  → Celery Worker 执行 AI 拆解
  → WebSocket/轮询推送进度
  → 结果保存到 PlotBreakdown 表
  → 前端展示拆解结果
```

## 二、核心文件

| 文件 | 职责 |
|------|------|
| `backend/app/api/v1/breakdown.py` | API 接口层 |
| `backend/app/tasks/breakdown_tasks.py` | Celery 异步任务 |
| `backend/app/models/plot_breakdown.py` | 数据模型 |
| `frontend/src/pages/user/Workspace/PlotTab/` | 前端组件 |

## 三、API 端点

| 端点 | 功能 |
|------|------|
| `POST /breakdown/start` | 启动单个批次拆解 |
| `POST /breakdown/start-all` | 批量启动所有 pending 批次 |
| `POST /breakdown/continue/{project_id}` | 继续拆解下一个 pending 批次 |
| `GET /breakdown/tasks/{taskId}` | 获取任务状态和进度 |
| `GET /breakdown/results/{batchId}` | 获取拆解结果 |
| `POST /breakdown/tasks/{taskId}/retry` | 重试失败任务 |
| `PATCH /breakdown/results/{batchId}/plot-points/{pointId}/status` | 更新剧情点状态 |

## 四、Celery 任务执行流程

`run_breakdown_task` 主函数流程：

1. **初始化** (0-5%) - 创建 Redis 日志发布器，更新状态为 running
2. **加载章节数据** (5-10%)
3. **加载 AI 资源文档** (12-15%) - methodology、output_style、template、qa_rules
4. **执行拆解** (20-90%) - 优先用 Agent 执行器，失败回退到 Skill 执行器
5. **保存结果** (90-100%) - 写入 PlotBreakdown 表，扣除积分

## 五、数据格式版本

### V1 格式（旧版 - 6字段分离）

```json
{
  "format_version": 1,
  "batch_id": "uuid",

  "conflicts": [
    {
      "id": "c1",
      "type": "人物冲突",
      "description": "主角与反派之间的权力斗争",
      "participants": ["主角", "反派"],
      "intensity": 8,
      "chapter_range": [1, 3]
    }
  ],

  "plot_hooks": [
    {
      "id": "h1",
      "type": "悬念",
      "description": "主角发现了一个神秘的线索",
      "chapter": 2,
      "impact": 7
    }
  ],

  "characters": [
    {
      "id": "ch1",
      "name": "张三",
      "role": "主角",
      "traits": ["勇敢", "善良", "冲动"],
      "relationships": {"李四": "好友", "王五": "敌人"},
      "arc": "从懦弱到勇敢的成长"
    }
  ],

  "scenes": [
    {
      "id": "s1",
      "location": "古老的城堡",
      "time": "深夜",
      "description": "月光透过破碎的窗户洒进大厅",
      "characters": ["主角", "神秘人"],
      "chapter": 1,
      "mood": "紧张、神秘"
    }
  ],

  "emotions": [
    {
      "emotion": "愤怒",
      "intensity": 8,
      "character": "主角",
      "trigger": "发现被背叛",
      "chapter": 3
    }
  ],

  "episodes": [
    {
      "episode_number": 1,
      "title": "第一集标题",
      "main_conflict": "主要冲突描述",
      "key_scenes": ["关键场景1", "关键场景2"],
      "chapter_range": [1, 3],
      "conflicts": [],
      "plot_hooks": [],
      "characters": [],
      "scenes": [],
      "emotions": []
    }
  ]
}
```

### V2 格式（新版 - 统一剧情点）

```json
{
  "format_version": 2,
  "batch_id": "uuid",

  "plot_points": [
    {
      "id": 1,
      "scene": "豪华酒店大堂",
      "characters": ["叶凡", "林婉儿", "陈总"],
      "event": "叶凡当众揭穿陈总的阴谋，展示证据",
      "hook_type": "打脸爽点",
      "episode": 1,
      "status": "unused",
      "source_chapter": 1
    },
    {
      "id": 2,
      "scene": "公司会议室",
      "characters": ["叶凡", "王秘书"],
      "event": "叶凡展现商业才能，提出关键方案",
      "hook_type": "初露锋芒",
      "episode": 1,
      "status": "unused",
      "source_chapter": 2
    }
  ],

  "qa_status": "PASS",
  "qa_score": 85,
  "qa_report": {
    "status": "PASS",
    "score": 85,
    "dimensions": {
      "completeness": { "pass": true, "score": 90, "issues": [] },
      "accuracy": { "pass": true, "score": 85, "issues": [] },
      "hook_quality": { "pass": true, "score": 80, "issues": ["部分钩子强度偏弱"] }
    },
    "issues": [],
    "suggestions": ["可增加更多高强度情绪钩子"]
  },
  "qa_retry_count": 0
}
```

### 格式对比

| 维度 | V1（旧版） | V2（新版） |
|------|-----------|-----------|
| 数据结构 | 6个独立字段，分类存储 | 统一 `plot_points` 数组 |
| 关联性 | 需要手动关联各字段 | 每个点自包含所有信息 |
| 剧集规划 | 单独的 `episodes` 字段 | `episode` 字段内嵌在每个点 |
| 状态追踪 | 无 | `status: used/unused` |
| 来源追溯 | 分散在各字段 | `source_chapter` 统一标记 |
| 质检集成 | 可选，独立流程 | 内置 `qa_status/qa_score/qa_report` |
| 适用场景 | 需要分类分析的场景 | 剧本生成、快速迭代 |

## 六、情绪钩子类型（hook_type）

| 类型 | 说明 |
|------|------|
| 打脸蓄力 | 为打脸做铺垫 |
| 打脸爽点 | 当场打脸的爽感 |
| 碾压爽点 | 实力碾压对手 |
| 金手指觉醒 | 获得特殊能力 |
| 身份曝光 | 真实身份揭露 |
| 身份提升 | 地位/身份提升 |
| 初露锋芒 | 首次展现实力 |
| 绝境反杀 | 绝境中逆转 |
| 虐心痛点 | 情感虐心 |
| 悬念开场 | 制造悬念 |
| 反转爽点 | 剧情反转 |
| 甜宠时刻 | 甜蜜互动 |
| 吃醋争风 | 情感冲突 |
| 先知优势 | 利用先知信息 |
| 复仇成功 | 复仇达成 |
| 底牌爆发 | 隐藏实力爆发 |
| 危机出现 | 危机降临 |
| 真相揭露 | 真相大白 |
| 误会产生 | 误会冲突 |

## 七、批次状态流转

```
pending → queued → processing → completed
                            ↘ failed → (retry) → queued
```

| 状态 | 含义 |
|------|------|
| `pending` | 待拆解 |
| `queued` | 已排队 |
| `processing` | 拆解中 |
| `completed` | 已完成 |
| `failed` | 失败 |

## 八、系统评估

### 优点

1. **架构设计合理** - API → Celery → AI 执行器分层清晰
2. **积分系统设计好** - 后扣费模式，使用锁防止并发超支
3. **灵活的执行策略** - Agent/Skill 双模式，自动回退
4. **防重复提交** - 检查已有任务状态

### 待优化项

1. **积分预扣逻辑** - API 层预扣 + 任务层扣费，需确认幂等性
2. **批量任务失败处理** - 中间失败时积分回滚不完善
3. **配置字段冗余** - 新旧版本兼容字段过多
4. **质检重试限制** - 缺少明确的最大重试次数控制
5. **并发控制** - `concurrent_limit` 字段未实际使用

## 九、相关文档

- [改编方法论](./webtoon-skill/adapt-method-breakdown.md)
- [AI 技能系统](./../.trellis/spec/backend/ai-skills.md)
