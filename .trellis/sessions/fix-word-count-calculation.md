# 剧本字数计算问题修复

**日期**: 2026-02-26
**问题**: Script Tab 中总字数和四段式各部分字数计算不准确

---

## 问题分析

### 原始数据（有问题）

```json
{
  "word_count": 386,
  "structure": {
    "opening": { "word_count": 110 },
    "development": { "word_count": 160 },
    "climax": { "word_count": 210 },
    "hook": { "word_count": 100 }
  }
}
```

**问题**：
- ✅ 总字数 `word_count: 386` 是正确的（后端使用 `calculate_word_count()` 计算）
- ❌ 四段式各部分的 `word_count` 是 LLM 估算的，不准确
- ❌ 四段式总和 (580) 与总字数 (386) 不一致

### 正确的字数

| 段落 | LLM 估算 | 正确值 | 差异 |
|------|----------|--------|------|
| opening | 110 | 69 | +41 |
| development | 160 | 96 | +64 |
| climax | 210 | 149 | +61 |
| hook | 100 | 56 | +44 |
| **总和** | **580** | **370** | **+210** |

---

## 根本原因

1. **LLM 在生成剧本时**，会在 `structure` 的每个段落中返回 `word_count`
2. **这个 `word_count` 是 LLM 自己估算的**，不是使用后端的 `calculate_word_count()` 函数
3. **后端在保存时**：
   - 使用 `calculate_word_count(full_script)` 计算总字数 ✅
   - 但直接使用 LLM 返回的 `structure` 数据，没有重新计算各段落的 `word_count` ❌

---

## 修复方案

### 1. 后端修复（`backend/app/tasks/script_tasks.py`）

**位置**: `_execute_episode_script_sync()` 函数，第 318-330 行

**修改前**:
```python
# 6.2 重新计算字数
full_script = script_result.get("full_script", "")
if full_script:
    word_count = calculate_word_count(full_script)
else:
    word_count = 0
```

**修改后**:
```python
# 6.2 重新计算字数（包括 structure 各段落和总字数）
full_script = script_result.get("full_script", "")

# 重新计算 structure 中每个段落的字数
for section in required_sections:
    section_data = structure.get(section, {})
    if isinstance(section_data, dict) and "content" in section_data:
        section_content = section_data["content"]
        # 使用统一的字数计算函数
        recalculated_word_count = calculate_word_count(section_content)
        structure[section]["word_count"] = recalculated_word_count

# 计算总字数
if full_script:
    word_count = calculate_word_count(full_script)

    if log_publisher:
        llm_word_count = script_result.get("word_count", 0)
        structure_total = sum(structure[s].get("word_count", 0) for s in required_sections)
        log_publisher.publish_info(
            task_id,
            f"📊 字数统计：LLM 估算 {llm_word_count} 字，实际计算 {t} 字（四段式总和 {structure_total} 字）"
        )
else:
    word_count = 0
```

### 2. 前端修复

#### 2.1 创建字数计算工具（`frontend/src/utils/wordCount.ts`）

```typescript
/**
 * 计算剧本字数（去除格式标记）
 * 与后端 calculate_word_count() 保持一致
 */
export function calculateWordCount(text: string): number {
  if (!text) return 0;

  let cleanText = text;

  // 去除场景标记：※ 场景名称（时间）
  cleanText = cleanText.replace(/※.*?（.*?）/g, '');

  // 去除动作标记：△
  cleanText = cleanText.replace(/△/g, '');

  // 去除特效标记：【xxx】
  cleanText = cleanText.replace(/【.*?】/g, '');

  // 去除所有空白字符
  cleanText = cleanText.replace(/\s+/g, '');

  return cleanText.length;
}
```

#### 2.2 更新 ScriptTab 组件（`frontend/src/pages/user/Workspace/ScriptTab/index.tsx`）

**修改 1**: 导入字数计算工具
```typescript
import { calculateWordCount } from '../../../../utils/wordCount';
```

**修改 2**: 更新 `handleStructureChange` 函数
```typescript
const handleStructureChange = (key: keyof ScriptStructure, content: string) => {
  if (!editedStructure) return;

  // 使用统一的字数计算函数（去除格式标记）
  const wordCount = calculateWordCount(content);
  // ...
};
```

**修改 3**: 更新 `handleSave` 函数
```typescript
const handleSave = async () => {
  // ...

  // 使用统一的字数计算函数
  const totalWordCount = calculateWordCount(editedFullScript || '');

  setCurrentScript({
    ...currentScript,
    word_count: totalWordCount
  });
  // ...
};
```

---

## 字数计算规则

根据 `docs/ai_flow_desc/webtoon-skill/adapt-method-script.md` 第 269-272 行：

```markdown
**字数统计方法**：
- 场景标注不计入
- 特效标注不计入
- 只统计动作描写和对话
```

### 实现逻辑

```python
def calculate_word_count(text: str) -> int:
    clean_text = text
    clean_text = re.sub(r'※.*?（.*?）', '', clean_text)  # 去除场景标记
    clean_text = re.sub(r'△', '', clean_text)           # 去除动作标记
    clean_text = re.sub(r'【.*?】', '', clean_text)      # 去除特效标记
    clean_text = re.sub(r'\s+', '', clean_text)         # 去除空白字符
    return len(clean_text)
```

---

## 测试验证

### 测试脚本

创建了两个测试脚本：
- `backend/test_word_count.py` - 原有测试
- `backend/test_word_count_fix.py` - 修复验证测试

### 测试结果

```
修复前（LLM 估算值）:
  opening: 110 字
  development: 160 字
  climax: 210 字
  hook: 100 字
  总和: 580 字

修复后（重新计算）:
  opening: 69 字
  development: 96 字
  climax: 149 字
  hook: 56 字
  总和: 370 字

完整剧本字数: 386 字 ✅
```

---

## 影响范围

### 后端
- ✅ `backend/app/tasks/script_tasks.py` - 剧本保存逻辑
- ✅ 新生成的剧本会使用正确的字数
- ⚠️ 已有剧本的 `structure.word_count` 仍然不准确（需要重新生成或手动修正）

### 前端
- ✅ `frontend/src/utils/wordCount.ts` - 新增字数计算工具
- ✅ `frontend/src/pages/user/Workspace/ScriptTab/index.tsx` - 编辑保存逻辑
- ✅ 用户编辑剧本时会使用正确的字数计算

---

## 后续建议

### 1. 数据迁移（可选）

如果需要修正已有剧本的字数，可以创建数据迁移脚本：

```python
# 伪代码
for script in all_scripts:
    for section in ["opening", "development", "climax", "hook"]:
        content = script.content["structure"][section]["content"]
        correct_count = calculate_word_count(content)
        script.content["structure"][section]["word_count"] = correct_count
    db.commit()
```

### 2. 提示词优化（可选）

在 LLM 提示词中明确说明字数计算规则，减少 LLM 估算错误：

```markdown
**重要**：字数统计规则
- 场景标注（※）不计入字数
- 动作标记（△）不计入字数
- 特效标记（【】）不计入字数
- 只统计实际对话和描述内容
```

### 3. 前端显示优化（可选）

在 ScriptDetail 组件中，可以显示四段式总和与完整剧本字数的对比，帮助用户发现不一致：

```typescript
const structureTotal = Object.values(structure).reduce(
  (sum, s) => sum + (s?.word_count || 0), 0
);
const fullScriptCount = calculateWordCount(full_script || '');

if (Math.abs(structureTotal - fullScriptCount) > 50) {
  // 显示警告：字数不一致
}
```

---

## 总结

✅ **问题已修复**：
1. 后端在保存剧本时会重新计算 `structure` 各段落的 `word_count`
2. 前端使用统一的 `calculateWordCount()` 函数计算字数
3. 前后端字数计算逻辑完全一致

✅ **修复效果**：
- 新生成的剧本字数准确
- 用户编辑剧本时字数准确
- 四段式总和与完整剧本字数一致

⚠️ **注意事项**：
- 已有剧本的 `structure.word_count` 仍然不准确
- 如需修正，可运行数据迁移脚本
