# 端到端测试手册

**测试日期**: 2026-02-08
**测试目的**: 验证剧集拆解配置系统的完整功能

---

## 前置条件

- [x] 后端服务运行中（端口 8000）
- [x] 前端服务运行中（Vite）
- [x] 数据库配置已导入（3个系统默认配置）
- [ ] 有可用的测试项目和批次数据

---

## 测试步骤

### 步骤 1: 验证配置加载

**目标**: 验证 ConfigSelector 组件能正确加载配置列表

1. 打开浏览器访问前端地址（通常是 http://localhost:5173）
2. 登录系统（使用 admin 或测试用户）
3. 进入 Workspace 页面
4. 切换到 "剧情拆解" 标签页
5. 找到配置选择器区域

**预期结果**:
- ✅ 看到三个配置选择器：
  - 改编方法 (Adapt Method)
  - 质检规则 (Quality Rule)
  - 输出风格 (Output Style)
- ✅ 每个选择器都有默认值：
  - adapt_method_default
  - qa_breakdown_default
  - output_style_default
- ✅ 每个选项显示 "系统默认" 标签（蓝色）

**验证点**:
```
□ 配置选择器正确渲染
□ 默认值正确显示
□ 下拉列表可以打开
□ 配置描述正确显示
□ "系统默认" 标签正确显示
```

---

### 步骤 2: 验证配置选择

**目标**: 验证用户可以选择不同的配置

1. 点击 "改编方法" 下拉框
2. 查看可用选项列表
3. 选择一个配置（如果有多个）
4. 重复步骤 1-3 测试其他两个选择器

**预期结果**:
- ✅ 下拉列表正确显示所有可用配置
- ✅ 每个配置显示：
  - Key（配置键名）
  - Description（配置描述）
  - 标签（自定义 或 系统默认）
- ✅ 选择后，选择器显示更新

**验证点**:
```
□ 下拉列表正确显示
□ 配置信息完整
□ 选择功能正常
□ 状态更新正确
```

---

### 步骤 3: 验证配置传递（启动拆解）

**目标**: 验证配置正确传递到后端

**前置条件**: 需要有一个 pending 状态的批次

1. 在 Workspace 中选择一个 pending 批次
2. 确认配置选择器的值（记录当前选择）
3. 点击 "启动拆解" 按钮
4. 观察控制台日志

**预期结果**:
- ✅ 拆解任务成功启动
- ✅ 控制台显示 "配置已应用" 消息
- ✅ 任务状态变为 "running"

**验证点**:
```
□ 启动拆解成功
□ 配置应用消息显示
□ 任务状态正确更新
□ 无错误信息
```

---

### 步骤 4: 验证配置持久化（后端验证）

**目标**: 验证配置正确保存到数据库

**在后端执行以下命令**:

```bash
cd backend
source venv/bin/activate
python -c "
from app.core.database import AsyncSessionLocal
from app.models.ai_task import AITask
from sqlalchemy import select
import asyncio

async def check_latest_task():
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(AITask)
            .where(AITask.task_type == 'breakdown')
            .order_by(AITask.created_at.desc())
            .limit(1)
        )
        task = result.scalar_one_or_none()
        if task:
            print(f'任务 ID: {task.id}')
            print(f'任务状态: {task.status}')
            print(f'配置内容:')
            print(f'  - adapt_method_key: {task.config.get(\"adapt_method_key\")}')
            print(f'  - quality_rule_key: {task.config.get(\"quality_rule_key\")}')
            print(f'  - output_style_key: {task.config.get(\"output_style_key\")}')
        else:
            print('未找到拆解任务')

asyncio.run(check_latest_task())
"
```

**预期结果**:
- ✅ 显示最新的拆解任务
- ✅ 配置字段正确保存：
  - adapt_method_key: adapt_method_default
  - quality_rule_key: qa_breakdown_default
  - output_style_key: output_style_default

**验证点**:
```
□ 任务记录存在
□ 配置字段完整
□ 配置值正确
```

---

### 步骤 5: 验证配置注入（Pipeline 执行）

**目标**: 验证配置正确传递到 PipelineExecutor

**查看 Celery 日志**:

```bash
# 查看最近的 Celery 日志
tail -f backend/logs/celery.log | grep -E "(adapt_method|quality_rule|output_style)"
```

**预期结果**:
- ✅ 日志显示配置加载信息
- ✅ 配置正确注入到执行上下文

**验证点**:
```
□ 配置加载日志存在
□ 配置值正确
□ 无错误信息
```

---

## 高级测试：用户自定义配置

### 步骤 6: 创建自定义配置

**目标**: 验证用户可以创建和使用自定义配置

1. 进入 "AI 配置" 管理页面
2. 点击 "新建配置" 按钮
3. 填写配置信息：
   - Key: `adapt_method_custom_test`
   - Category: `adapt_method`
   - Description: `测试用自定义改编方法`
   - Value: 复制 adapt_method_default 的 value 并修改
4. 保存配置

**预期结果**:
- ✅ 配置创建成功
- ✅ 配置列表显示新配置

**验证点**:
```
□ 配置创建成功
□ 配置显示在列表中
```

---

### 步骤 7: 验证自定义配置优先级

**目标**: 验证用户自定义配置优先于系统默认

1. 返回 Workspace 页面
2. 刷新页面（重新加载配置）
3. 打开 "改编方法" 下拉框
4. 查看配置列表

**预期结果**:
- ✅ 自定义配置显示在列表中
- ✅ 自定义配置显示 "自定义" 标签（紫色）
- ✅ 自定义配置排在系统默认配置之前

**验证点**:
```
□ 自定义配置显示
□ 标签正确（紫色 "自定义"）
□ 排序正确（自定义优先）
```

---

### 步骤 8: 使用自定义配置启动拆解

**目标**: 验证自定义配置可以正常使用

1. 选择自定义配置 `adapt_method_custom_test`
2. 启动拆解任务
3. 验证配置传递（重复步骤 4）

**预期结果**:
- ✅ 任务成功启动
- ✅ 配置字段保存为 `adapt_method_custom_test`

**验证点**:
```
□ 自定义配置可选择
□ 任务启动成功
□ 配置正确保存
```

---

## 测试结果记录

### 基础功能测试

| 测试项 | 状态 | 备注 |
|--------|------|------|
| 配置加载 | ⏳ 待测试 | |
| 配置选择 | ⏳ 待测试 | |
| 配置传递 | ⏳ 待测试 | |
| 配置持久化 | ⏳ 待测试 | |
| 配置注入 | ⏳ 待测试 | |

### 高级功能测试

| 测试项 | 状态 | 备注 |
|--------|------|------|
| 创建自定义配置 | ⏳ 待测试 | |
| 自定义配置优先级 | ⏳ 待测试 | |
| 使用自定义配置 | ⏳ 待测试 | |

---

## 问题记录

### 发现的问题

1. **问题描述**:
   - 现象:
   - 重现步骤:
   - 预期行为:
   - 实际行为:

2. **问题描述**:
   - 现象:
   - 重现步骤:
   - 预期行为:
   - 实际行为:

---

## 测试总结

**测试完成时间**:
**测试人员**:
**总体评价**:

### 通过的测试
- [ ] 配置加载
- [ ] 配置选择
- [ ] 配置传递
- [ ] 配置持久化
- [ ] 配置注入
- [ ] 创建自定义配置
- [ ] 自定义配置优先级
- [ ] 使用自定义配置

### 未通过的测试
-

### 需要改进的地方
-

---

## 附录：快速验证脚本

### 验证数据库配置

```bash
cd backend
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
        print(f'系统默认配置: {len(configs)} 个')
        for cfg in configs:
            print(f'  - {cfg.key} ({cfg.category})')

asyncio.run(check())
"
```

### 验证最新任务配置

```bash
cd backend
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
            print(f'任务 ID: {task.id}')
            print(f'配置: {json.dumps(task.config, indent=2, ensure_ascii=False)}')

asyncio.run(check())
"
```
