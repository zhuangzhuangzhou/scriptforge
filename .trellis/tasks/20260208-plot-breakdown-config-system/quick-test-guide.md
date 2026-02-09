# 配置系统快速测试指南

**测试时间**: 预计 10-15 分钟
**测试环境**: ✅ 已就绪

---

## 🚀 开始测试

### 1. 打开浏览器

访问：http://localhost:5173

### 2. 登录系统

使用以下任一账号：
- **管理员**: admin
- **测试用户**: debug_user_001 或 zhuangzhuang

### 3. 进入 Workspace

1. 点击左侧菜单 "工作区" 或 "Workspace"
2. 选择项目："我的治愈系游戏"
3. 切换到 "剧情拆解" 标签页

---

## ✅ 测试检查点

### 检查点 1: 配置选择器显示

**位置**: 剧情拆解标签页，批次列表下方

**检查项**:
```
□ 看到三个配置选择器
  □ 改编方法 (Adapt Method)
  □ 质检规则 (Quality Rule)
  □ 输出风格 (Output Style)

□ 每个选择器显示默认值
  □ adapt_method_default
  □ qa_breakdown_default
  □ output_style_default

□ 每个选择器有 tooltip 说明（鼠标悬停在 ⓘ 图标上）
```

**截图**: 如果可以，截图保存为 `screenshot-1-selector.png`

---

### 检查点 2: 配置下拉列表

**操作**: 点击每个配置选择器的下拉箭头

**检查项**:
```
□ 改编方法下拉列表
  □ 显示 adapt_method_default
  □ 显示配置描述
  □ 显示 "系统默认" 标签（蓝色/青色）

□ 质检规则下拉列表
  □ 显示 qa_breakdown_default
  □ 显示配置描述
  □ 显示 "系统默认" 标签

□ 输出风格下拉列表
  □ 显示 output_style_default
  □ 显示配置描述
  □ 显示 "系统默认" 标签
```

**截图**: `screenshot-2-dropdown.png`

---

### 检查点 3: 启动拆解（配置传递）

**操作**:
1. 选择一个 pending 批次（批次 1-6 任选一个）
2. 确认配置选择器的值（保持默认）
3. 点击 "启动拆解" 按钮

**检查项**:
```
□ 控制台显示 "配置已应用" 消息
□ 任务成功启动
□ 批次状态变为 "running" 或 "processing"
□ 无错误提示
```

**控制台日志**: 打开浏览器开发者工具（F12），查看 Console 标签

---

### 检查点 4: 验证配置保存（后端）

**在终端执行**:

```bash
cd /Users/zhouqiang/Data/jim/backend
source venv/bin/activate
python -c "
from app.core.database import AsyncSessionLocal
from app.models.ai_task import AITask
from sqlalchemy import select
import asyncio

async def check():
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(AITask)
            .where(AITask.task_type == 'breakdown')
            .order_by(AITask.created_at.desc())
            .limit(1)
        )
        task = result.scalar_one_or_none()
        if task:
            print(f'✅ 任务 ID: {task.id}')
            print(f'✅ 任务状态: {task.status}')
            print(f'✅ 配置内容:')
            print(f'   - adapt_method_key: {task.config.get(\"adapt_method_key\")}')
            print(f'   - quality_rule_key: {task.config.get(\"quality_rule_key\")}')
            print(f'   - output_style_key: {task.config.get(\"output_style_key\")}')
        else:
            print('❌ 未找到拆解任务')

asyncio.run(check())
" 2>&1 | grep -E "(✅|❌)"
```

**预期输出**:
```
✅ 任务 ID: xxx
✅ 任务状态: queued 或 running
✅ 配置内容:
   - adapt_method_key: adapt_method_default
   - quality_rule_key: qa_breakdown_default
   - output_style_key: output_style_default
```

---

## 🎯 测试结果

### 基础功能测试

| 检查点 | 状态 | 备注 |
|--------|------|------|
| 配置选择器显示 | ⏳ | |
| 配置下拉列表 | ⏳ | |
| 启动拆解 | ⏳ | |
| 配置保存验证 | ⏳ | |

### 发现的问题

1. **问题 1**:
   - 描述:
   - 严重程度: 🔴高 / 🟡中 / 🟢低

2. **问题 2**:
   - 描述:
   - 严重程度:

---

## 📝 测试完成后

### 如果测试全部通过 ✅

在终端告诉我：
```
测试通过，所有检查点都正常
```

我会帮你：
1. 更新验证报告
2. 标记 Checkpoint 5 完成
3. 准备提交代码

### 如果发现问题 ❌

告诉我具体的问题：
```
检查点 X 失败：[具体描述]
```

我会帮你：
1. 分析问题原因
2. 提供修复方案
3. 重新测试

---

## 🔧 辅助工具

### 查看最新任务配置

```bash
cd /Users/zhouqiang/Data/jim/backend
source venv/bin/activate
python -c "
from app.core.database import AsyncSessionLocal
from app.models.ai_task import AITask
from sqlalchemy import select
import asyncio
import json

async def check():
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(AITask)
            .where(AITask.task_type == 'breakdown')
            .order_by(AITask.created_at.desc())
            .limit(1)
        )
        task = result.scalar_one_or_none()
        if task:
            print(json.dumps({
                'task_id': task.id,
                'status': task.status,
                'config': task.config
            }, indent=2, ensure_ascii=False))

asyncio.run(check())
"
```

### 查看系统配置列表

```bash
cd /Users/zhouqiang/Data/jim/backend
source venv/bin/activate
python -c "
from app.core.database import AsyncSessionLocal
from app.models.ai_configuration import AIConfiguration
from sqlalchemy import select
import asyncio

async def check():
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(AIConfiguration)
            .where(AIConfiguration.user_id.is_(None))
            .where(AIConfiguration.category.in_(['adapt_method', 'quality_rule', 'prompt_template']))
        )
        configs = result.scalars().all()
        for cfg in configs:
            print(f'{cfg.key} ({cfg.category})')

asyncio.run(check())
"
```

---

## 准备好了吗？

1. 打开浏览器：http://localhost:5173
2. 登录系统
3. 进入 Workspace
4. 开始测试！

测试完成后告诉我结果 🚀
