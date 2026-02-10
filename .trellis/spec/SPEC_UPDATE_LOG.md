# 规范更新日志

记录所有规范文档的更新历史。

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

**更新人**: AI Assistant
**审查状态**: 待审查
**相关任务**: 模型管理系统 v1.1.0 - 移除加密功能

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
