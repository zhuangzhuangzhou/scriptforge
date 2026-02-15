# 规范更新日志

记录所有规范文档的更新历史。

## 2026-02-12 - WorkflowEditor 可视化编辑器

### 更新的规范

1. **`frontend/index.md`** - 更新
   - 新增 WorkflowEditor 组件文档
   - 目录结构、核心功能、使用示例

### 学到的关键知识

#### 1. React Hooks 条件调用问题

**问题**：`useMemo` 在条件返回 (`if (!step) return ...`) 之后调用，违反 Hooks 规则

**解决**：将所有 Hooks 移到条件返回之前，在 Hook 内部处理 null 情况

```tsx
// ❌ 错误
if (!step) return <Empty />;
const inputFields = useMemo(() => { ... }, [step]);

// ✅ 正确
const inputFields = useMemo(() => {
  if (!step) return [];
  // ...
}, [step]);
if (!step) return <Empty />;
```

#### 2. 步骤 ID 修改时的匹配问题

**问题**：使用 `steps.map(s => s.id === selectedStepId ? updated : s)` 更新步骤，当用户修改 ID 后匹配失败

**解决**：使用索引定位而非 ID 匹配

```tsx
const selectedStepIndex = value.steps.findIndex(s => s.id === selectedStepId);
const newSteps = [...value.steps];
newSteps[selectedStepIndex] = updatedStep;
```

#### 3. 变量引用顺序

**问题**：工作流步骤只能引用之前步骤的输出，不能引用后续步骤

**解决**：传递 `currentStepIndex`，只提取之前步骤的变量引用

```tsx
const previousSteps = currentStepIndex > 0 ? allSteps.slice(0, currentStepIndex) : [];
const variableRefs = extractVariableRefs(previousSteps);
```

---

## 2026-02-15 - 任务/批次状态规范统一

### 更新的规范

1. **`backend/index.md`** - 更新
   - 新增任务/批次状态规范与映射规则
   - 指定 `normalize_task_status()` 与 `map_task_status_to_batch()` 为单一来源

2. **`frontend/index.md`** - 更新
   - 新增状态常量来源 (`frontend/src/constants/status.ts`)
   - 明确 UI 只依赖批次状态展示“拆解中”

### 学到的关键知识

#### 1. 状态分层能减少耦合

任务状态用于执行控制，批次状态用于 UI 展示。两者分层后，前端不会因为任务短暂波动而抖动。

#### 2. 映射规则必须集中管理

散落的字符串判断会导致 `processing/running` 混用，必须通过统一映射函数维护。

## 2026-02-08 - 移除加密功能的经验总结

### 更新的规范

1. **`backend/security.md`** - 新增
   - 应用层加密 vs 数据库级加密的决策指南
   - API Key 脱敏显示模式
   - 数据库迁移中的敏感数据处理
   - 安全检查清单

2. **`backend/database.md`** - 新增
   - 破坏性变更的多阶段迁移策略
   - 字段类型变更的安全做法
   - 加密字段迁移的常见错误和正确做法
   - 迁移文件命名和注释规范
   - 数据迁移脚本模式

### 学到的关键知识

#### 1. 应用层加密的权衡

**问题**：
- 密钥管理复杂（ENCRYPTION_KEY 环境变量）
- 密钥丢失导致数据永久丢失
- 部署复杂度增加

**解决方案**：
- 优先使用数据库级加密（PostgreSQL TDE）
- 或使用文件系统加密
- 仅在特殊场景下使用应用层加密

**影响**：
- 简化了部署流程
- 降低了密钥管理风险
- 但需要更严格的数据库安全措施

#### 2. 破坏性迁移的处理

**问题**：
直接重命名加密字段为明文字段，导致数据无法使用。

**错误做法**：
```python
# ❌ 直接重命名
op.alter_column('credentials', 'api_key_encrypted',
                new_column_name='api_key')
```

**正确做法**：
```python
# ✅ 方案 1：先解密再迁移
# 1. 添加新列
# 2. 解密并复制数据
# 3. 删除旧列

# ✅ 方案 2：要求重新创建（测试环境）
# 在文档中明确说明破坏性变更
```

**预防措施**：
- 在迁移文件中添加清晰的警告注释
- 提供数据导出脚本
- 在测试环境先验证

#### 3. API Key 脱敏显示

**模式**：
```python
def mask_api_key(api_key: str) -> str:
    if len(api_key) <= 10:
        return "***"
    prefix = api_key[:3]
    suffix = api_key[-3:]
    return f"{prefix}***...***{suffix}"
```

**应用场景**：
- API 响应
- 管理界面
- 日志记录
- 错误消息

**不脱敏的场景**：
- 实际调用第三方 API
- 用户首次创建凭证的确认

### 相关文件

**代码变更**：
- `backend/app/models/ai_model_credential.py`
- `backend/app/ai/adapters/model_config_service.py`
- `backend/app/api/v1/admin/credentials.py`
- `backend/alembic/versions/ecc01e4bf4bc_*.py`

**文档**：
- `docs/ENCRYPTION_REMOVED.md`
- `docs/ENCRYPTION_REMOVAL_SUMMARY.md`
- `CHANGELOG_ENCRYPTION_REMOVAL.md`

### 适用场景

这些规范适用于：
- 需要存储敏感数据（API Key、密码等）
- 需要进行破坏性数据库迁移
- 需要在加密和明文存储之间做决策

### 未来改进

可能的改进方向：
- 添加数据库级加密的具体实施指南
- 添加更多迁移模式（如数据类型转换）
- 添加安全审计的自动化工具

---

## 2026-02-13 - 使用 GitHub Issues 管理待办事项

### 更新的规范

1. **`CLAUDE.md`** - 更新
   - 添加 GitHub Issues 工作流说明

### 学到的关键知识

#### 1. 使用 `gh CLI` 管理 Issues

**优势**：
- Issues 是持久的，不受 Claude Code 会话限制
- 标签系统提供灵活的分类方式
- 可以让团队成员和 AI 快速了解待办事项

**常用命令**：
```bash
# 查看 Issues 列表
gh issue list

# 创建 Issue（交互式）
gh issue create

# 创建 Issue（一步到位）
gh issue create -t "标题" -b "描述内容" -l "bug"

# 查看 Issue 详情
gh issue view 6

# 关闭 Issue
gh issue close 6

# 编辑 Issue
gh issue edit 6 --add-label "priority:high"
```

#### 2. 创建和使用自定义标签

```bash
# 创建优先级标签
gh label create "priority:high" --color "d73a4a" --description "高优先级"
gh label create "priority:medium" --color "fbca04" --description "中优先级"
gh label create "priority:low" --color "0e8a16" --description "低优先级"

# 查看现有标签
gh label list
```

#### 3. GitHub Issues 作为任务跟踪

**工作流程**：
1. 发现问题或待办 → 创建 Issue
2. 设置优先级和类型标签
3. 开发时参考 Issue 列表
4. 完成后关闭 Issue

**标签推荐**：
| 标签类型 | 示例 |
|---------|------|
| 类型 | `bug`, `enhancement`, `feature`, `documentation` |
| 优先级 | `priority:high`, `priority:medium`, `priority:low` |
| 模块 | `frontend`, `backend`, `database`, `api` |

### 相关文件

**更新的文件**：
- `.trellis/spec/SPEC_UPDATE_LOG.md`

**创建的 Issues**：
- #6 积分双重扣费风险
- #7 批量任务失败时积分未回滚
- #8 质检循环缺少最大重试限制
- #9 并发控制参数未生效
- #10 JSON 解析正则匹配问题
- #11 清理废弃的兼容字段
- #12 统一错误信息解析方式

### 适用场景

这些规范适用于：
- 跨会话的任务跟踪
- 团队协作中的待办管理
- Bug 和待办事项的持久化存储
- 使用 GitHub 作为任务管理工具

---

## 2026-02-13 - Glass UI 组件完善与积分系统问题修复

### 更新的规范

1. **`frontend/index.md`** - 更新
   - 新增 GlassRangePicker 组件
   - 添加 Glass 组件常见问题（双重边框、占位符颜色）
   - 修复 WorkflowEditor 文档位置

2. **`backend/database.md`** - 更新
   - 新增积分扣费重复问题
   - 新增字段命名不一致问题

### 学到的关键知识

#### 1. Glass 组件双重边框问题

**问题**：GlassInput 组件显示两层边框

**原因**：Ant Design 的 `ant-input-affix-wrapper` 本身有边框，内部的 `ant-input` 也有边框

**修复**：为 affix-wrapper 内部的 input 移除边框

```css
.glass-input-wrapper .ant-input-affix-wrapper .ant-input {
  border: none !important;
  background: transparent !important;
  box-shadow: none !important;
}
```

#### 2. 积分重复扣费

**问题**：用户积分被重复扣除两次

**原因**：API 层预扣积分后，Celery 任务完成时又执行了一次扣费

**修复**：明确扣费时机，删除 Celery 任务中的重复扣费代码

#### 3. 积分显示不一致

**问题**：前端显示的积分与账单详情中的余额不一致

**原因**：后端 `/auth/me` 返回 ORM 对象时，`balance` 字段是 DECIMAL(10,2) 类型（值为 0），而 `credits` 字段才是实际积分

**修复**：手动构建响应，映射字段

```python
@router.get("/me")
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    return UserResponse(
        balance=current_user.credits,  # 使用 credits 作为积分余额
        ...
    )
```

### 相关文件

**修复的代码**：
- `frontend/src/components/ui/GlassInput.tsx` - 修复双重边框
- `frontend/src/components/ui/GlassSelect.tsx` - 修复占位符颜色
- `frontend/src/components/ui/GlassDatePicker.tsx` - 新增组件
- `frontend/src/pages/admin/Logs/*.tsx` - 使用 Glass 组件
- `backend/app/api/v1/auth.py` - 修复字段映射
- `backend/app/tasks/breakdown_tasks.py` - 删除重复扣费

### 适用场景

这些规范适用于：
- 创建新的 Glass UI 组件
- 排查前端组件样式问题
- 实现积分扣费逻辑
- 修复前后端数据不一致问题

---

**更新人**: AI Assistant (Claude Opus 4.6)
**审查状态**: 待审查
**相关任务**: 系统修复与 Glass UI 组件完善

## 2026-02-12 - Agent/Skill/Resource 三层架构完善

### 更新的规范

1. **`backend/ai-skills.md`** - 新增第 12 章
   - 简化架构：Agent / Skill / Resource 三层模式
   - 循环工作流配置详解
   - 输入类型自动转换机制
   - 用户友好的日志消息规范
   - 完整调用流程图

### 学到的关键知识

#### 1. 三层架构职责划分

| 层级 | 职责 | 存储位置 |
|------|------|----------|
| **Resource** | AI 资源文档（方法论、规则、模板） | `AIResource` 表 |
| **Agent** | 工作流编排（循环、条件、重试） | `SimpleAgent` 表 |
| **Skill** | Prompt 模板 + 输入/输出定义 | `Skill` 表 |

**调用关系**：
```
Resource (加载文档) → Agent (编排工作流) → Skill (执行单步)
```

#### 2. 输入类型自动转换 ⚠️ GOTCHA

**问题**：
Skill 的 `prompt_template` 使用 Python `str.format()`，所有输入必须是字符串。
但 Agent 步骤之间传递的数据可能是 `list` 或 `dict`。

**解决方案**：
在 `SimpleSkillExecutor` 中自动转换：

```python
processed_inputs = {}
for key, value in inputs.items():
    if isinstance(value, str):
        processed_inputs[key] = value
    elif isinstance(value, (list, dict)):
        processed_inputs[key] = json.dumps(value, ensure_ascii=False, indent=2)
    elif value is None:
        processed_inputs[key] = ""
    else:
        processed_inputs[key] = str(value)
```

#### 3. 用户友好的日志消息

**问题**：
技术性日志消息（如 `循环迭代 1/3`）对用户不友好。

**解决方案**：
| 场景 | ❌ 技术性消息 | ✅ 用户友好消息 |
|------|-------------|----------------|
| Agent 启动 | `开始执行 Agent: breakdown_agent` | `🤖 启动智能流程：剧情拆解 Agent` |
| 循环迭代 | `循环迭代 1/3` | `🔄 第 1 轮处理（共 3 轮）` |
| 质检通过 | `循环在第 1 轮满足退出条件` | `✅ 质量检查通过，第 1 轮完成` |
| 达到上限 | `循环达到最大迭代次数 3，强制退出` | `⚠️ 已完成 3 轮处理，结果可能需要人工复核` |

**原则**：
1. 使用 emoji 增加可读性
2. 避免暴露内部变量名
3. 条件不满足时不发布日志（避免用户困惑）
4. 失败时给出下一步建议

#### 4. 模型导入错误

**问题**：
`SimpleAgentExecutor` 导入了错误的模型类 `Agent`，应该是 `SimpleAgent`。

**修复**：
```python
# ❌ 错误
from app.models.agent import Agent

# ✅ 正确
from app.models.agent import SimpleAgent
```

### 相关文件

**修改的代码**：
- `backend/app/ai/simple_executor.py`
  - 修复 `SimpleAgent` 导入
  - 添加输入类型自动转换
  - 优化日志消息

**更新的规范**：
- `.trellis/spec/backend/ai-skills.md` - 新增第 12 章

### 适用场景

这些规范适用于：
- 使用 Agent 编排多个 Skill
- 实现循环质检工作流
- 优化用户端日志显示
- 排查 Agent/Skill 执行问题

---

**更新人**: AI Assistant (Claude Opus 4.6)
**审查状态**: 待审查
**相关任务**: Agent 驱动的剧情拆解流程优化

---

## 2026-02-10 - AI Skill 系统开发规范

### 更新的规范

1. **`backend/ai-skills.md`** - 新增
   - Skill 系统架构和核心概念
   - Skill 开发规范（命名、结构、错误处理）
   - Prompt 工程最佳实践
   - SkillLoader 自动加载机制
   - 质检类 Skill 特殊模式
   - 常见错误和解决方案
   - 性能优化和测试规范

2. **`backend/index.md`** - 更新
   - 添加 AI 模块规范的详细说明
   - 强调 Skill 文件命名规范的重要性

### 学到的关键知识

#### 1. Skill 文件命名规范 ⚠️ CRITICAL

**问题**：
创建的 Skill 文件没有被 SkillLoader 自动加载。

**原因**：
SkillLoader 只加载以 `_skill.py` 结尾的文件（见 `skill_loader.py:39`）

```python
# skill_loader.py
for filename in os.listdir(skills_dir):
    if filename.endswith("_skill.py") and filename != "base_skill.py":
        # 只有这些文件会被加载
```

**错误做法**：
```bash
# ❌ 不会被加载
breakdown_aligner.py
webtoon_aligner.py
```

**正确做法**：
```bash
# ✅ 会被自动加载
breakdown_aligner_skill.py
webtoon_aligner_skill.py
```

**影响**：
- 如果文件名不符合规范，Skill 不会被加载
- 调用 `get_skill()` 会返回 `None`
- 不会有任何错误提示，难以排查

**预防措施**：
- 创建测试脚本验证 Skill 是否被加载
- 在开发文档中明确说明命名规范
- 考虑在 SkillLoader 中添加警告日志

#### 2. JSON 解析容错机制

**问题**：
不同 AI 模型的输出格式不一致，有的会用 Markdown 代码块包裹 JSON。

**解决方案**：
```python
def _parse_response(self, response: str) -> Dict[str, Any]:
    try:
        # 提取 JSON（某些模型会返回 Markdown 代码块）
        if "```json" in response:
            response = response.split("```json")[1].split("```")[0].strip()
        elif "```" in response:
            response = response.split("```")[1].split("```")[0].strip()

        result = json.loads(response)
        return {"status": "SUCCESS", "data": result}
    except Exception as e:
        logger.error(f"响应解析失败: {e}, 原始响应: {response[:500]}")
        return {
            "status": "ERROR",
            "error": str(e),
            "raw_response": response  # 保留原始响应用于调试
        }
```

**为什么需要这样做**：
1. 不同模型的输出格式可能不同
2. 保留原始响应便于调试
3. 避免因解析失败导致整个流程中断

#### 3. 温度参数选择

**发现**：
不同类型的 Skill 需要不同的温度参数。

**最佳实践**：
| 任务类型 | 推荐温度 | 原因 |
|---------|---------|------|
| **质检/审核** | 0.3 | 需要稳定、一致的输出 |
| **创作/生成** | 0.7 | 需要创造性和多样性 |
| **分类/提取** | 0.5 | 平衡准确性和灵活性 |

**示例**：
```python
# 质检类 Skill（如 Breakdown-Aligner、Webtoon-Aligner）
response = await model_adapter.generate_async(
    prompt=prompt,
    temperature=0.3,  # 低温度确保稳定输出
    max_tokens=2048
)

# 创作类 Skill（如场景生成、对话创作）
response = await model_adapter.generate_async(
    prompt=prompt,
    temperature=0.7,  # 高温度增加创造性
    max_tokens=4096
)
```

#### 4. 质检类 Skill 的特殊模式

**双基准检查模式**：
质检类 Skill 需要对照多个基准文档进行检查。

**示例**（Webtoon-Aligner）：
```python
# 基准1: plot_breakdown.md（剧情拆解）
# 基准2: adapt_method.md（改编方法论）

prompt = f"""
### 核心基准文档

#### 1. 剧情拆解（plot_breakdown.md）- 最重要的基准
{self._format_plot_breakdown(plot_breakdown)}

#### 2. 改编方法论（adapt_method.md）
{self._format_adapt_method(adapt_method)}

### 检查要求
严格基于以上两个基准进行检查...
"""
```

**批次检查模式**：
支持一次检查多个单元（如多集剧本）。

```python
context = {
    "batch_number": 1,
    "episode_range": (1, 5),  # 第1-5集
    "episodes_content": [...]  # 多集内容
}
```

**跨单元连贯性检查**：
检查相邻单元之间的衔接。

```python
context = {
    "current_episode": {...},
    "previous_episode": {...}  # 用于检查连贯性
}
```

#### 5. Prompt 工程最佳实践

**结构化 Prompt 模板**：
```python
prompt = f"""你是一名资深的{角色描述}，负责{任务描述}。

### 任务目标
{明确的目标描述}

### 输入数据
{格式化的输入数据}

### 检查标准
{详细的检查标准或规则}

### 输出格式（必须严格遵循）
{{
    "field1": "说明",
    "field2": "说明"
}}

### 要求
1. 要求1
2. 要求2

请开始执行。
"""
```

**关键要素**：
1. 角色设定：明确 AI 的身份和专业领域
2. 任务目标：清晰描述要完成什么
3. 输入数据：结构化展示输入
4. 检查标准：详细的评判标准
5. 输出格式：明确的 JSON Schema
6. 执行要求：具体的约束条件

### 相关文件

**新增代码**：
- `backend/app/ai/skills/webtoon_aligner_skill.py` (11KB)
- `backend/test_skills_loading.py`

**重命名文件**：
- `backend/app/ai/skills/breakdown_aligner.py` → `breakdown_aligner_skill.py`

**新增文档**：
- `docs/agent-implementation-analysis.md`
- `docs/agent-skills-usage-guide.md`
- `docs/webtoon-aligner-implementation-report.md`

**更新规范**：
- `.trellis/spec/backend/ai-skills.md` (新增)
- `.trellis/spec/backend/index.md` (更新)

### 实现成果

**Webtoon-Aligner Skill**：
- ✅ 11 维度一致性检查
- ✅ 批次级检查（支持多集同时检查）
- ✅ 跨集连贯性验证
- ✅ 基于双基准检查（plot_breakdown + adapt_method）
- ✅ 结构化 JSON 输出
- ✅ 完善的错误处理机制

**验证结果**：
```bash
✅ 已加载的 Skills 数量: 10

✅ breakdown_aligner 已加载
✅ webtoon_aligner 已加载
```

### 适用场景

这些规范适用于：
- 开发新的 AI Skill
- 实现质检类 Skill（多维度检查）
- 实现批次处理 Skill
- 排查 Skill 加载问题
- 优化 Prompt 工程

### 未来改进

可能的改进方向：
- 添加 Skill 单元测试框架
- 添加 Skill 性能监控
- 支持 Skill 热加载（无需重启）
- 添加 Skill 版本管理
- 支持自定义检查规则配置

---

**更新人**: AI Assistant (Claude Sonnet 4.5)
**审查状态**: 待审查
**相关任务**: Webtoon-Aligner 实现

---

## 2026-02-12 - 纯积分制系统实现

### 更新的规范

1. **`backend/database.md`** - 新增章节
   - 配置读取性能优化（内存缓存 + TTL）
   - 同步函数的数据库操作规范
   - 配置读取的异常处理
   - 积分扣费失败的处理
   - 前端数据的准确性

### 学到的关键知识

#### 1. 配置查询需要加缓存

**问题**：每次扣费都查询数据库，高并发下性能差

**解决**：使用 60 秒内存缓存

```python
_config_cache: Optional[dict] = None
_config_cache_ts: float = 0
_CONFIG_CACHE_TTL = 60

async def get_credits_config(db):
    global _config_cache, _config_cache_ts
    now = time.monotonic()
    if _config_cache and (now - _config_cache_ts) < _CONFIG_CACHE_TTL:
        return _config_cache
    # 从数据库读取...
```

#### 2. 同步函数内部不要自行 commit

**问题**：函数内部 commit 导致事务边界混乱

**解决**：由调用方统一管理事务

```python
# ✅ 正确：不 commit
def consume_credits_sync(db, user_id):
    user.credits -= amount
    return {"success": True}

# 调用方管理事务
def run_task():
    consume_credits_sync(db, user_id)
    db.commit()  # 统一 commit
```

#### 3. 配置读取必须有异常兜底

**问题**：数据库表不存在时直接抛异常

**解决**：try/except 回退默认值

```python
try:
    result = db.query(SystemConfig).all()
except Exception as e:
    logger.warning(f"读取配置失败，使用默认值: {e}")
    return _DEFAULT_CONFIG
```

#### 4. 扣费失败需要详细日志

**问题**：只打印警告无法排查问题

**解决**：logger.error 记录 user_id 和 task_id

```python
logger.error(
    f"积分扣费失败: user={user_id}, task={task_id}, "
    f"reason={credits_result['message']}"
)
```

#### 5. 前端数据计算必须精确

**问题**：用分页数据做聚合不准确

**解决**：后端直接返回聚合结果

```python
# 后端
monthly_consumed = await db.execute(
    select(func.sum(BillingRecord.credits))
    .where(...)
)
return {"monthly_consumed": monthly_consumed}
```
