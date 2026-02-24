# webtoon_script Skill 输出格式优化总结

## 优化日期
2026-02-24

## 优化目标
解决 webtoon_script Skill 输出格式不一致的问题，确保 LLM 输出、后端处理、前端显示三者完全匹配。

---

## 实施内容

### 1. 更新 Skill Prompt 模板

**文件**: `backend/app/core/init_simple_system.py`

**主要变更**:

#### 1.1 明确 JSON 输出格式
- 使用英文键名：`opening`（起）、`development`（承）、`climax`（转）、`hook`（钩）
- 每个段落包含 `content` 和 `word_count` 两个字段
- `content` 保留所有格式标记（※、△、【】）

#### 1.2 详细的格式说明
```json
{
  "episode_number": 1,
  "title": "第1集标题",
  "word_count": 650,
  "structure": {
    "opening": {
      "content": "※ 场景（时间）\\n△ 动作\\n角色：\\"对话\\"",
      "word_count": 120
    },
    "development": { "content": "...", "word_count": 180 },
    "climax": { "content": "...", "word_count": 220 },
    "hook": { "content": "...", "word_count": 130 }
  },
  "full_script": "【起】开场冲突\\n...\\n【卡黑】",
  "scenes": ["场景1", "场景2"],
  "characters": ["角色1", "角色2"],
  "hook_type": "悬念类型"
}
```

#### 1.3 更新 output_schema
- 详细定义 `structure` 的嵌套结构
- 明确每个段落的 `content` 和 `word_count` 字段类型

---

### 2. 添加后端验证和修正逻辑

**文件**: `backend/app/tasks/script_tasks.py`

#### 2.1 新增字数计算函数
```python
def calculate_word_count(text: str) -> int:
    """计算剧本字数（去除格式标记）"""
    # 去除场景标记：※ 场景名称（时间）
    # 去除动作标记：△
    # 去除特效和段落标记：【起】【承】【转】【钩】【卡黑】等
    # 去除空白字符
    return len(clean_text)
```

**测试结果**:
- 完整剧本（289 字符）→ 171 字（去除标记后）
- 单段内容（70 字符）→ 46 字
- 纯对话（48 字符）→ 45 字
- 空字符串 → 0 字

#### 2.2 添加数据验证逻辑
在剧本生成完成后、保存到数据库之前：

1. **验证 structure 完整性**
   - 检查是否包含 `opening`, `development`, `climax`, `hook` 四个段落
   - 缺少任何段落则抛出异常

2. **重新计算字数**
   - 使用 `calculate_word_count()` 函数计算准确字数
   - 记录 LLM 估算值和实际计算值的差异

3. **验证场景和角色**
   - 检查 `scenes` 和 `characters` 是否为空
   - 为空时记录警告日志

4. **验证结尾标记**
   - 检查 `full_script` 是否包含【卡黑】标记
   - 缺少时记录警告日志

5. **发布验证日志**
   - 通过 RedisLogPublisher 发布验证结果
   - 显示字数、场景数、角色数统计信息

---

## 验证测试

### 测试 1: structure 完整性验证
✅ 完整的 structure 验证通过
✅ 不完整的 structure 正确检测到缺少段落

### 测试 2: 字数计算
✅ 完整剧本: 95 字（预期 80-120）
✅ 空字符串: 0 字

### 测试 3: 场景和角色提取
✅ 场景列表: 3 个
✅ 角色列表: 3 个

### 测试 4: 结尾标记验证
✅ 正确检测【卡黑】标记的存在与否

### 测试 5: JSON 格式验证
✅ 所有必需字段都存在
✅ structure 包含所有必需段落
✅ 所有段落都包含 content 和 word_count 字段

---

## 前端兼容性

### 类型定义已匹配
**文件**: `frontend/src/types.ts`

```typescript
export interface ScriptStructure {
  opening: { content: string; word_count: number };      // 【起】
  development: { content: string; word_count: number };  // 【承】
  climax: { content: string; word_count: number };       // 【转】
  hook: { content: string; word_count: number };         // 【钩】
}

export interface EpisodeScript {
  id?: string;
  episode_number: number;
  title: string;
  word_count: number;
  structure: ScriptStructure;
  full_script: string;
  scenes: string[];
  characters: string[];
  hook_type: string;
  // ...
}
```

✅ 前端类型定义完全匹配新的输出格式
✅ 无需修改前端代码

---

## 数据流程

```
1. LLM 生成剧本（JSON 格式）
   ↓
2. 后端验证 structure 完整性
   ↓
3. 后端重新计算字数（去除格式标记）
   ↓
4. 后端验证场景、角色、结尾标记
   ↓
5. 保存到数据库（使用验证后的数据）
   ↓
6. 前端显示（两种视图）
   - 四段式结构视图：使用 structure
   - 完整剧本视图：使用 full_script
```

---

## 关键改进点

### 1. 统一键名
- ❌ 旧版：中文键名（"起"、"承"、"转"、"钩"）
- ✅ 新版：英文键名（opening, development, climax, hook）

### 2. 准确字数
- ❌ 旧版：直接使用 `len(full_script)`，包含所有标记
- ✅ 新版：使用 `calculate_word_count()`，去除格式标记

### 3. 数据验证
- ❌ 旧版：无验证，直接保存
- ✅ 新版：验证完整性、重新计算字数、检查必需字段

### 4. 日志记录
- ❌ 旧版：无详细日志
- ✅ 新版：记录 LLM 估算值 vs 实际计算值，显示统计信息

---

## 预期效果

### 1. LLM 输出
- 生成完整的 JSON 对象
- structure 和 full_script 都保留格式标记
- 提供场景和角色列表

### 2. 后端处理
- 重新计算准确的字数
- 验证数据完整性
- 记录验证日志

### 3. 前端显示
- 四段式结构视图正确显示
- 完整剧本视图正确显示
- 元信息统计准确

### 4. 用户体验
- 生成的剧本格式规范
- 字数统计准确
- 编辑功能完整

---

## 后续优化建议

### 1. 添加 structure 和 full_script 一致性检查
- 检查 structure 中的内容是否与 full_script 中对应段落一致
- 不一致时记录警告或自动修正

### 2. 优化字数计算逻辑
- 考虑是否需要计算每个段落的字数
- 验证段落字数是否符合要求（起 100-150，承 150-200，转 200-250，钩 100-150）

### 3. 添加格式标记验证
- 检查是否包含必需的格式标记（※、△、【】）
- 检查格式标记的使用是否规范

### 4. 前端显示优化
- 支持格式标记的渲染（如高亮显示场景、动作、对话）
- 支持分段编辑时的实时字数统计

---

## 相关文件

| 文件 | 修改内容 |
|------|----------|
| `backend/app/core/init_simple_system.py` | 更新 webtoon_script Skill 的 Prompt 模板和 output_schema |
| `backend/app/tasks/script_tasks.py` | 添加字数计算函数和数据验证逻辑 |
| `backend/test_word_count.py` | 字数计算函数测试脚本 |
| `backend/test_script_format_validation.py` | 完整的格式验证测试套件 |
| `frontend/src/types.ts` | 前端类型定义（已匹配，无需修改） |

---

## 总结

本次优化成功解决了 webtoon_script Skill 输出格式不一致的问题：

1. ✅ 统一使用英文键名，匹配前端类型定义
2. ✅ 添加后端字数计算和验证逻辑
3. ✅ 保留格式标记，支持前端渲染
4. ✅ 详细的日志记录，便于调试
5. ✅ 完整的测试验证，确保功能正确

系统现在能够：
- 生成规范的 JSON 格式剧本
- 准确计算剧本字数（去除格式标记）
- 验证数据完整性和一致性
- 支持前端两种视图的显示需求
