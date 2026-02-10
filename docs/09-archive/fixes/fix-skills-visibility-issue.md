# 修复技能列表"暂无可用技能"问题

## 问题描述

在剧情拆解配置弹窗中，SkillSelector 组件显示"暂无可用技能"，但数据库中实际存在 8 个激活的技能。

## 问题分析

### 1. 前端调用流程

**组件**: `frontend/src/components/SkillSelector.tsx`

```tsx
const loadSkills = async () => {
    setLoading(true);
    try {
        const res = await skillsApi.getAvailableSkills(category);
        if (res.data && res.data.skills) {
            setSkills(res.data.skills);
        }
    } catch (err) {
        console.error('加载技能失败:', err);
        message.error('无法加载技能列表');
    } finally {
        setLoading(false);
    }
};
```

**API 调用**: `frontend/src/services/api.ts`

```typescript
export const skillsApi = {
  getAvailableSkills: async (category?: string) => {
    return api.get('/skills/available', { params: { category } });
  }
};
```

### 2. 后端 API 实现

**文件**: `backend/app/api/v1/skills_user.py`

**端点**: `GET /api/v1/skills/available`

```python
@router.get("/available")
async def get_available_skills(
    category: Optional[str] = None,
    visibility: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取可用的Skills列表（根据权限过滤）"""
    # 获取公共Skills + 用户自己的Skills
    query = select(Skill).where(
        Skill.is_active == True,
        or_(
            Skill.visibility == 'public',  # 公共Skills
            Skill.owner_id == current_user.id,  # 用户自己的Skills
        )
    )
    
    if category:
        query = query.where(Skill.category == category)
    
    # ...
```

### 3. 数据库状态

查询数据库发现，8 个技能中有 6 个的 `visibility` 字段为 `None`：

```
冲突点提取 (conflict_extraction)
  category: breakdown
  visibility: None  ❌
  is_builtin: True

剧情钩子识别 (plot_hook_identification)
  category: breakdown
  visibility: None  ❌
  is_builtin: True

人物分析 (character_analysis)
  category: breakdown
  visibility: None  ❌
  is_builtin: True

场景识别 (scene_identification)
  category: breakdown
  visibility: None  ❌
  is_builtin: True

情绪点提取 (emotion_extraction)
  category: breakdown
  visibility: None  ❌
  is_builtin: True

剧集规划 (episode_planning)
  category: script
  visibility: None  ❌
  is_builtin: True

场景生成 (scene_generation)
  category: script
  visibility: public  ✅
  is_builtin: True

对话生成 (dialogue_writing)
  category: script
  visibility: public  ✅
  is_builtin: True
```

### 4. 问题根因

API 的查询条件是：

```python
or_(
    Skill.visibility == 'public',  # 公共Skills
    Skill.owner_id == current_user.id,  # 用户自己的Skills
)
```

由于：
- `visibility` 为 `None`，不等于 `'public'`
- `owner_id` 是系统用户 ID（`00000000-0000-0000-0000-000000000001`），不等于当前登录用户的 ID

所以这 6 个技能不会被返回，导致前端显示"暂无可用技能"。

## 修复方案

### 方案 1：修复数据（已采用）

将所有内置技能的 `visibility` 设置为 `'public'`，使其对所有用户可见。

**修复脚本**: `backend/fix_skills_visibility.py`

```python
import asyncio
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.skill import Skill

async def fix_skills_visibility():
    async with AsyncSessionLocal() as db:
        # 查找所有 visibility 为 None 的内置技能
        result = await db.execute(
            select(Skill).where(
                Skill.is_builtin == True,
                Skill.visibility.is_(None)
            )
        )
        skills = result.scalars().all()
        
        print(f'找到 {len(skills)} 个需要修复的技能')
        
        for skill in skills:
            print(f'  修复: {skill.display_name} ({skill.name})')
            skill.visibility = 'public'
        
        await db.commit()
        print('\n修复完成！')

asyncio.run(fix_skills_visibility())
```

**执行结果**:
```
找到 6 个需要修复的技能
  修复: 冲突点提取 (conflict_extraction)
  修复: 剧情钩子识别 (plot_hook_identification)
  修复: 人物分析 (character_analysis)
  修复: 场景识别 (scene_identification)
  修复: 情绪点提取 (emotion_extraction)
  修复: 剧集规划 (episode_planning)

修复完成！
```

### 方案 2：修改 API 查询逻辑（备选）

如果不想修改数据，可以修改 API 的查询条件，将内置技能也包含进来：

```python
query = select(Skill).where(
    Skill.is_active == True,
    or_(
        Skill.visibility == 'public',  # 公共Skills
        Skill.owner_id == current_user.id,  # 用户自己的Skills
        Skill.is_builtin == True,  # 内置Skills（新增）
    )
)
```

**优缺点对比**:

| 方案 | 优点 | 缺点 |
|------|------|------|
| 方案1：修复数据 | 数据一致性好，符合设计规范 | 需要执行数据修复脚本 |
| 方案2：修改查询 | 不需要修改数据 | 逻辑不够清晰，可能导致混淆 |

**选择**: 采用方案 1，因为内置技能本来就应该是公开的。

## 修复验证

### 1. 数据库验证

```bash
cd backend
./venv/bin/python check_skills.py
```

**结果**: 所有 8 个技能的 `visibility` 都是 `'public'`

### 2. API 验证

```bash
curl -X GET "http://localhost:8000/api/v1/skills/available?category=breakdown" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**预期结果**: 返回 5 个 breakdown 类别的技能

### 3. 前端验证

1. 打开剧情拆解配置弹窗
2. 查看技能选择器
3. 应该显示 5 个可选技能，而不是"暂无可用技能"

## 预防措施

### 1. 数据库约束

建议在 `skills` 表的 `visibility` 字段添加默认值：

```python
# backend/app/models/skill.py
class Skill(Base):
    # ...
    visibility = Column(String(50), default='public')  # 添加默认值
```

### 2. 数据初始化

在初始化脚本中明确设置 `visibility`：

```python
# backend/app/core/init_skills.py
skill = Skill(
    name="conflict_extraction",
    display_name="冲突点提取",
    # ...
    visibility='public',  # 明确设置
    is_builtin=True
)
```

### 3. API 文档

在 API 文档中明确说明 `visibility` 字段的含义和可选值：

- `'public'`: 所有用户可见
- `'private'`: 仅创建者可见
- `'shared'`: 指定用户可见

## 相关文件

- `frontend/src/components/SkillSelector.tsx` - 技能选择器组件
- `frontend/src/services/api.ts` - API 服务定义
- `backend/app/api/v1/skills_user.py` - 技能 API 实现
- `backend/app/models/skill.py` - 技能数据模型
- `backend/fix_skills_visibility.py` - 数据修复脚本
- `backend/check_skills.py` - 数据检查脚本

## 总结

"暂无可用技能"问题的根本原因是数据库中内置技能的 `visibility` 字段为 `None`，导致 API 查询时被过滤掉。通过将这些技能的 `visibility` 设置为 `'public'`，问题得到解决。

建议在后续开发中：
1. 为 `visibility` 字段添加数据库默认值
2. 在数据初始化时明确设置该字段
3. 完善 API 文档，说明字段含义

---

**修复时间**: 2026-02-09
**修复人**: AI Assistant
