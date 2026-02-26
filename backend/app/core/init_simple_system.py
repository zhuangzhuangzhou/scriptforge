"""初始化简化的 Skill & Agent 系统

在应用启动时自动创建内置的 Skills 和 Agents。
"""
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models.skill import Skill
from app.models.agent import SimpleAgent
import uuid
from datetime import datetime

# 系统内置资源的固定 owner_id
SYSTEM_OWNER_ID = uuid.UUID("00000000-0000-0000-0000-000000000000")


# ==================== 内置 Skills 定义 ====================

BUILTIN_SKILLS = [
    {
        "name": "webtoon_breakdown",
        "display_name": "网文改编剧情拆解",
        "description": "基于网文改编方法论，一次性完成剧情拆解、分集标注、情绪钩子识别",
        "category": "breakdown",
        "is_template_based": True,
        "system_prompt": """你是资深网文改编漫剧编辑，精通冲突识别、情绪钩子提取、分集节奏规划。

【核心判断标准】
- 核心冲突：只有"改变主角命运或关系"的才是核心冲突
- 高分钩子：能让观众"卧槽！"=10分，"爽/虐/急"=8-9分，"还行"=6-7分
- 分集原则：每集必须有钩子结尾，高强度钩子(9-10分)建议单独成集

输出格式由代码处理，你只需专注内容质量。""",
        "prompt_template": """### 任务
将小说第{start_chapter}-{end_chapter}章拆解为漫剧剧情点，集数从第 {start_episode} 集开始编号。

---

### 小说原文
{chapters_text}

---

### 上轮拆解结果
{previous_plot_points}

### 质检反馈（如有，必须针对性修正）
{qa_feedback}

**注意**：如果有质检反馈，请基于上轮结果进行针对性修正，不要从头重新拆解。

---

### 钩子类型定义
{hook_types}

---

### 钩子边界规则（易混淆类型区分）
{hook_boundary_rules}

---

### 类型特性指南
{genre_guidelines}

---

### 拆解思考步骤

**第一步：识别核心冲突**
快速浏览原文，标记改变主角处境或关系的冲突点。

**第二步：提取情绪钩子**
对每个冲突判断观众情绪反应，选择最准确的钩子类型。

**第三步：分集规划**
每集1-3个剧情点，结尾必须是钩子，确保"卡黑"效果。

**第四步：压缩检查**
删掉后故事仍完整的内容 → 删除；无情绪价值的内容 → 删除。

---

### 剧情点质量标准
1. 独立性：每个剧情点是一个相对完整的小场景
2. 推动力：推动主线发展、揭示关键信息、或改变人物关系
3. 情绪价值：有明确的情绪钩子，不能平淡过渡
4. 可视化：场景描述能转化为画面，避免纯心理活动
5. 字数控制：单个剧情点描述 30-50 字

---

### 改编方法论
{adapt_method}

### 输出风格
{output_style}

### 格式模板
{template}

### 示例
{example}

---

### 输出格式
**【关键要求】每行一个剧情点，使用管道符 | 分隔，禁止使用逗号分隔！**

格式：
剧情点序号|场景|角色|剧情|钩子|第X集

**【禁止事项】**
- ❌ 禁止使用逗号分隔，如"真相线索，第13集"
- ❌ 禁止添加任何额外符号


字段说明：
- 剧情点序号：从1开始连续编号
- 场景：具体场景名称
- 角色：用 / 分隔多个角色
- 剧情：简洁描述（30-50字）
- 钩子：只能从标准钩子类型中选择一个
- 集数：第X集（从 {start_episode} 开始）

### 输出示例
1|豪华酒店大堂|林浩/陈总|林浩当众揭穿陈总的商业欺诈，陈总脸色铁青|打脸爽点|第1集
2|公司会议室|林浩/秘书小王|林浩展示隐藏实力震惊全场，众人目瞪口呆|碾压爽点|第1集
3|地下停车场|林浩/神秘女子|神秘女子暗示林浩的真实身份后消失|悬念设置|第2集

请直接输出剧情点列表，每行一个。""",
        "input_schema": {
            "chapters_text": {"type": "string", "description": "章节文本内容"},
            "adapt_method": {"type": "string", "description": "改编方法论"},
            "output_style": {"type": "string", "description": "输出风格"},
            "template": {"type": "string", "description": "格式模板"},
            "example": {"type": "string", "description": "示例"},
            "previous_plot_points": {"type": "string", "description": "上一轮拆解结果（按集分组文本，可选）"},
            "qa_feedback": {"type": "string", "description": "上一轮质检反馈（文本，可选）"},
            "start_chapter": {"type": "integer", "description": "起始章节号"},
            "end_chapter": {"type": "integer", "description": "结束章节号"},
            "start_episode": {"type": "integer", "description": "起始集数（本批次从第几集开始编号）"},
            "hook_types": {"type": "string", "description": "钩子类型定义文档内容", "default": ""},
            "hook_boundary_rules": {"type": "string", "description": "钩子边界规则文档内容", "default": ""},
            "genre_guidelines": {"type": "string", "description": "类型特性指南文档内容", "default": ""}
        },
        "output_schema": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "scene": {"type": "string"},
                    "characters": {"type": "array"},
                    "event": {"type": "string"},
                    "hook_type": {"type": "string"},
                    "episode": {"type": "integer"},
                    "status": {"type": "string"},
                    "source_chapter": {"type": "integer"}
                }
            }
        },
        "model_config": {"temperature": 0.7, "max_tokens": 100000}
    },
    {
        "name": "breakdown_aligner",
        "display_name": "剧情拆解质量校验",
        "description": "基于改编方法论对剧情拆解进行质量检查，确保拆解符合方法论标准",
        "category": "breakdown",
        "is_template_based": True,
        "system_prompt": """你是严格的剧情拆解质量校验员，聚焦内容质量，不纠结格式问题。

【核心检查项】
1. 钩子类型是否准确
2. 是否遗漏高强度冲突
3. 分集节奏是否合理
4. 描述是否可视化

【修改意见规范】
✅ 正确："第3集第1点：'打脸蓄力' → '人物结交'，因为对方态度友好"
❌ 错误："钩子类型需要调整"（没说改成什么）""",
        "prompt_template": """### 质检任务
检查以下剧情拆解结果是否符合改编方法论标准。

---

### 待检查内容
{plot_points}

格式：序号|场景|角色|剧情|钩子|集数

---

### 原文对照
{chapters_text}

---

### 钩子类型定义
{hook_types}

---

### 钩子边界规则（易混淆类型区分）
{hook_boundary_rules}

---

### 类型特性指南
{genre_guidelines}

---

### 质检维度定义
{qa_dimensions}

---

### 改编方法论
{adapt_method}

---

### 质检步骤

**第一步：原文对照**
逐条核实每个剧情点是否能在原文中找到对应内容，有无曲解、遗漏、虚构。

**第二步：钩子验证**
检查每个钩子类型是否与剧情内容匹配，使用【钩子边界规则】逐一核对。

**第三步：密度评估**
统计核心冲突数量和高强度钩子(8-10分)数量，判断是否达标。

**第四步：分集审查**
检查每集是否有钩子结尾，高强度钩子是否合理分布。

**第五步：内容完整性**
检查场景是否具体、角色是否明确、事件描述是否清晰(30-50字)。

---

### 输出格式

**【关键要求】必须严格按照以下格式输出，禁止使用 Markdown 格式！**

请参考【质检维度定义】中的格式要求输出质检报告。

格式要点：
1. 【质检报告】总分 + 状态
2. 【维度1-8】评分 + 结果 + 说明
3. 【修改清单】具体可执行的修改建议

**标准格式模板**：
```
【质检报告】
总分：75
状态：通过

【维度1】冲突强度评估 评分 10 通过
说明：核心冲突识别准确

【维度2】情绪钩子识别 评分 6 未通过
说明：第3个剧情点钩子类型有误

【维度3】冲突密度达标性 评分 8 通过
说明：密度达标

...（维度4-8同理）

【修改清单】
1. 【剧情3】钩子类型错误：'打脸蓄力' → '人物结交'，因为对方态度友好
```

**格式约束**：
- 维度格式：`【维度N】名称 评分 XX 通过/未通过`（N为阿拉伯数字1-8）
- 状态词：只能使用"通过"或"未通过"
- 评分：只写数字，不要写"/12.5分"
- 禁止使用 Markdown 格式（###、**、- 等）
- 禁止添加额外符号（⭐、✓、✗等）

**禁止事项**：
❌ ### 维度1：冲突强度评估 ⭐⭐⭐
❌ **评估结果**：8/10分
❌ 【维度1】冲突强度评估 10/12.5分 ✓ 良好

请直接输出质检报告，不要输出 JSON。""",
        "input_schema": {
            "plot_points": {"type": "string", "description": "管道符分隔的剧情点列表（序号|场景|角色|剧情|钩子|集数）"},
            "chapters_text": {"type": "string", "description": "小说原文"},
            "adapt_method": {"type": "string", "description": "改编方法论"},
            "hook_types": {"type": "string", "description": "钩子类型定义文档内容", "default": ""},
            "hook_boundary_rules": {"type": "string", "description": "钩子边界规则文档内容", "default": ""},
            "genre_guidelines": {"type": "string", "description": "类型特性指南文档内容", "default": ""},
            "qa_dimensions": {"type": "string", "description": "质检维度定义文档内容", "default": ""}
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "status": {"type": "string", "enum": ["PASS", "FAIL"]},
                "score": {"type": "integer"},
                "dimensions": {"type": "array"},
                "issues": {"type": "array"},
                "fix_instructions": {"type": "array"}
            }
        },
        "model_config": {"temperature": 0.3, "max_tokens": 100000}
    },
    {
        "name": "webtoon_script",
        "display_name": "单集剧本创作",
        "description": "基于剧情点生成单集漫剧剧本，包含场景、动作、对话、特效标注",
        "category": "script",
        "is_template_based": True,
        "system_prompt": """你是资深网文改编漫剧编剧，精通"起承转钩"四段式剧本结构。

【核心原则】
- 开场3秒进冲突，结尾强制卡黑
- 对话单句不超过15字，禁止解释性对话
- 所有描述必须可视化，禁止心理独白

【剧本格式】
- 场景：※ 场景名称（时间）
- 动作：△ 动作描述
- 对话：角色名："对话内容"
- 特效：【特效类型】描述
- 结尾：【卡黑】""",
        "prompt_template": """### 任务
为第 {episode_number} 集创作漫剧剧本。

---

### 本集剧情点
{plot_points}

### 原文参考
{chapters_text}

### 改编方法论
{adapt_method}

---

### 类型特性指南
{genre_guidelines}

---

### 上一版剧本
{previous_script}

### 质检反馈
{qa_feedback}

**注意**：如有上一版剧本和质检反馈，请根据反馈意见修正问题，保留优点。

---

### 创作步骤

**第一步：理解剧情点**
本集核心钩子是什么？要传达什么情绪？结尾卡在哪里？

**第二步：设计四段结构**
- 【起】开场冲突（100-150字）：3秒抓眼球
- 【承】推进发展（150-200字）：为爽点铺垫
- 【转】反转高潮（200-250字）：情绪峰值
- 【钩】悬念结尾（100-150字）：强制卡黑

**第三步：视觉化检查**
逐句检查能否转化为画面，删除所有心理描写和抽象描述。

---

### 对话规范
- 单句不超过15字
- 同一角色连续不超过3句
- 禁止："让我告诉你..."、"我知道了"、"原来如此"

### 禁止事项
- 大段内心独白（>20字）
- 抽象描述："感觉很悲伤" → 改为"眼泪在眼眶打转"
- 过渡场景：不需要展示从A地到B地的过程

---

### 输出要求

请以 JSON 格式输出，包含以下字段：

```json
{{
  "episode_number": 1,
  "title": "第1集标题",
  "word_count": 650,
  "structure": {{
    "opening": {{
      "content": "※ 酒店大堂（日）\\n△ 林浩站在大堂中央，目光锐利地盯着陈总。\\n林浩：\\"陈总，您的账目有问题。\\"\\n陈总：\\"你在说什么？\\"\\n【特效：紧张气氛】",
      "word_count": 120
    }},
    "development": {{
      "content": "※ 公司会议室（日）\\n△ 林浩展示证据文件。\\n林浩：\\"这是您的转账记录。\\"\\n陈总：\\"这...这不可能！\\"\\n【特效：震惊】",
      "word_count": 180
    }},
    "climax": {{
      "content": "※ 酒店大堂（日）\\n△ 陈总跪地求饶。\\n陈总：\\"我错了，求你放过我！\\"\\n林浩：\\"晚了。\\"\\n△ 警察冲进来。\\n【特效：高潮音乐】",
      "word_count": 220
    }},
    "hook": {{
      "content": "※ 地下停车场（夜）\\n△ 神秘女子出现在林浩身后。\\n神秘女子：\\"你以为这就结束了？\\"\\n△ 林浩转身，震惊。\\n【卡黑】",
      "word_count": 130
    }}
  }},
  "full_script": "【起】开场冲突\\n※ 酒店大堂（日）\\n△ 林浩站在大堂中央，目光锐利地盯着陈总。\\n林浩：\\"陈总，您的账目有问题。\\"\\n陈总：\\"你在说什么？\\"\\n【特效：紧张气氛】\\n\\n【承】推进发展\\n※ 公司会议室（日）\\n△ 林浩展示证据文件。\\n林浩：\\"这是您的转账记录。\\"\\n陈总：\\"这...这不可能！\\"\\n【特效：震惊】\\n\\n【转】反转高潮\\n※ 酒店大堂（日）\\n△ 陈总跪地求饶。\\n陈总：\\"我错了，求你放过我！\\"\\n林浩：\\"晚了。\\"\\n△ 警察冲进来。\\n【特效：高潮音乐】\\n\\n【钩】悬念结尾\\n※ 地下停车场（夜）\\n△ 神秘女子出现在林浩身后。\\n神秘女子：\\"你以为这就结束了？\\"\\n△ 林浩转身，震惊。\\n【卡黑】",
  "scenes": ["酒店大堂", "公司会议室", "地下停车场"],
  "characters": ["林浩", "陈总", "神秘女子"],
  "hook_type": "悬念开场"
}}
```

**关键要求**：

1. **structure 字段**：
   - 使用英文键名：opening（起）、development（承）、climax（转）、hook（钩）
   - 每个段落包含 content 和 word_count 两个字段
   - content 必须保留所有格式标记（※、△、【】）
   - word_count 为估算值，后端会重新计算

2. **full_script 字段**：
   - 必须包含段落标题：【起】【承】【转】【钩】
   - 必须包含所有格式标记
   - 必须以【卡黑】结尾
   - 内容应与 structure 中的内容一致

3. **scenes 字段**：
   - 提取所有场景名称（不包括时间标记）
   - 按出现顺序排列
   - 示例：["酒店大堂", "公司会议室", "地下停车场"]

4. **characters 字段**：
   - 提取所有角色名称
   - 按出场顺序排列
   - 示例：["林浩", "陈总", "神秘女子"]

5. **hook_type 字段**：
   - 描述本集的悬念类型
   - 示例："打脸爽点"、"悬念开场"、"反转高潮"

**格式标记说明**：
- 场景标记：※ 场景名称（时间）
- 动作标记：△ 动作描述
- 对话格式：角色名："对话内容"
- 特效标记：【特效类型】描述
- 段落标记：【起】【承】【转】【钩】
- 结尾标记：【卡黑】""",
        "input_schema": {
            "plot_points": {"type": "string", "description": "管道符分隔的本集剧情点（序号|场景|角色|剧情|钩子|集数）"},
            "chapters_text": {"type": "string", "description": "原文参考"},
            "adapt_method": {"type": "string", "description": "改编方法论"},
            "episode_number": {"type": "integer", "description": "集数"},
            "genre_guidelines": {"type": "string", "description": "类型特性指南文档内容", "default": ""},
            "previous_script": {"type": "string", "description": "上一版剧本（用于修正）", "default": ""},
            "qa_feedback": {"type": "string", "description": "质检反馈意见（用于修正）", "default": ""}
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "episode_number": {"type": "integer"},
                "title": {"type": "string"},
                "word_count": {"type": "integer"},
                "structure": {
                    "type": "object",
                    "properties": {
                        "opening": {
                            "type": "object",
                            "properties": {
                                "content": {"type": "string"},
                                "word_count": {"type": "integer"}
                            }
                        },
                        "development": {
                            "type": "object",
                            "properties": {
                                "content": {"type": "string"},
                                "word_count": {"type": "integer"}
                            }
                        },
                        "climax": {
                            "type": "object",
                            "properties": {
                                "content": {"type": "string"},
                                "word_count": {"type": "integer"}
                            }
                        },
                        "hook": {
                            "type": "object",
                            "properties": {
                                "content": {"type": "string"},
                                "word_count": {"type": "integer"}
                            }
                        }
                    }
                },
                "full_script": {"type": "string"},
                "scenes": {"type": "array", "items": {"type": "string"}},
                "characters": {"type": "array", "items": {"type": "string"}},
                "hook_type": {"type": "string"}
            }
        },
        "model_config": {"temperature": 0.7, "max_tokens": 100000}
    },
    {
        "name": "webtoon_aligner",
        "display_name": "剧本质检",
        "description": "检查单集剧本是否符合漫剧改编标准，包括字数、结构、节奏、视觉化等",
        "category": "qa",
        "is_template_based": True,
        "system_prompt": """你是资深漫剧剧本质检专家，聚焦以下核心检查项：

【必检项目】
1. 字数范围：500-800字
2. 结构完整：起承转钩四段式
3. 开场冲突：3秒进冲突
4. 悬念结尾：必须有【卡黑】
5. 视觉化：无大段心理描写
6. 对话质量：单句≤15字

【修改意见规范】
必须具体可执行，说明"哪里"→"改成什么"。""",
        "prompt_template": """### 质检任务
检查以下剧本是否符合漫剧改编标准。

---

### 待检查剧本
{script}

### 原文参考
{chapters_text}

### 改编方法论
{adapt_method}

---

### 质检维度（总分100分）

**1. 字数范围（20分）**
- 总字数是否在500-800字范围内
- 过短则内容不足，过长则节奏拖沓

**2. 结构完整（25分）**
- 起承转钩四段式是否完整
- 各部分字数是否合理：起(100-150)、承(150-200)、转(200-250)、钩(100-150)

**3. 开场冲突（15分）**
- 是否3秒进冲突，无铺垫
- 开场是否从冲突最激烈的瞬间开始

**4. 悬念结尾（20分）**
- 是否有【卡黑】标记
- 悬念是否足够吸引观众看下一集

**5. 视觉化（10分）**
- 是否无大段心理描写（>20字）
- 所有描述是否可转化为画面

**6. 对话质量（10分）**
- 对话是否简短有力（单句≤15字）
- 是否无解释性对话和废话

---

### 输出格式

【质检报告】
总分：XX/100
状态：通过/不通过（80分以上通过）
实际字数：XXX字

【各维度评分】
1. 字数范围：XX/20 - 说明
2. 结构完整：XX/25 - 说明
3. 开场冲突：XX/15 - 说明
4. 悬念结尾：XX/20 - 说明
5. 视觉化：XX/10 - 说明
6. 对话质量：XX/10 - 说明

【问题清单】（必须具体可执行）
1. [问题类型] 位置：原内容 → 修改为 → 具体新内容
2. ...

【整体评价】
简要总结剧本质量和主要改进方向

请直接输出质检报告，不要输出 JSON。""",
        "input_schema": {
            "script": {"type": "string", "description": "结构化文本格式的剧本"},
            "chapters_text": {"type": "string", "description": "原文参考"},
            "adapt_method": {"type": "string", "description": "改编方法论"}
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "status": {"type": "string"},
                "score": {"type": "integer"},
                "dimensions": {"type": "object"},
                "fix_instructions": {"type": "array"},
                "summary": {"type": "string"}
            }
        },
        "model_config": {"temperature": 0.3, "max_tokens": 100000}
    }
]


# ==================== 内置 Agents 定义 ====================
#
# 变量引用语法说明：
# - ${context.xxx} : 从上下文获取输入参数
# - ${variable} : 引用上一步的输出，变量不存在时会报错
# - ${variable:} : 引用上一步的输出，变量不存在时返回空字符串（用于循环首轮）
# - ${variable:默认值} : 引用上一步的输出，变量不存在时返回默认值
#

BUILTIN_AGENTS = [
    {
        "name": "breakdown_agent",
        "display_name": "剧情拆解 Agent",
        "description": "智能剧情拆解：拆解 → 质检 → 循环，直到质量达标",
        "category": "breakdown",
        "workflow": {
            "type": "loop",
            "max_iterations": 3,
            "exit_condition": "qa_result.qa_status == 'PASS' and qa_result.qa_score >= 70",
            "steps": [
                {
                    "id": "breakdown",
                    "skill": "webtoon_breakdown",
                    "inputs": {
                        "chapters_text": "${context.chapters_text}",
                        "adapt_method": "${context.adapt_method}",
                        "output_style": "${context.output_style}",
                        "template": "${context.template}",
                        "example": "${context.example}",
                        # 循环首轮这两个变量不存在，使用 : 语法返回空字符串
                        "previous_plot_points": "${plot_points:}",
                        "qa_feedback": "${qa_result:}",
                        "start_chapter": "${context.start_chapter}",
                        "end_chapter": "${context.end_chapter}",
                        "start_episode": "${context.start_episode}",
                        # 新增资源参数
                        "hook_types": "${context.hook_types}",
                        "hook_boundary_rules": "${context.hook_boundary_rules}",
                        "genre_guidelines": "${context.genre_guidelines}"
                    },
                    "output_key": "plot_points",
                    "on_fail": "stop",
                    "max_retries": 1
                },
                {
                    "id": "qa",
                    "skill": "breakdown_aligner",
                    "inputs": {
                        "plot_points": "${plot_points}",
                        "chapters_text": "${context.chapters_text}",
                        "adapt_method": "${context.adapt_method}",
                        # 新增资源参数
                        "hook_types": "${context.hook_types}",
                        "hook_boundary_rules": "${context.hook_boundary_rules}",
                        "genre_guidelines": "${context.genre_guidelines}",
                        "qa_dimensions": "${context.qa_dimensions}"
                    },
                    "output_key": "qa_result",
                    "on_fail": "skip",
                    "max_retries": 0
                }
            ]
        }
    },
    {
        "name": "script_agent",
        "display_name": "剧本创作 Agent",
        "description": "基于剧情点生成高质量单集剧本，支持质检和润色",
        "category": "script",
        "workflow": {
            "type": "loop",
            "max_iterations": 2,
            "exit_condition": "qa_result.qa_status == 'PASS' and qa_result.qa_score >= 80",
            "steps": [
                {
                    "id": "script",
                    "skill": "webtoon_script",
                    "condition": "_iteration == 1",
                    "inputs": {
                        "plot_points": "${context.plot_points}",
                        "chapters_text": "${context.chapters_text}",
                        "adapt_method": "${context.adapt_method}",
                        "episode_number": "${context.episode_number}"
                    },
                    "output_key": "script_result",
                    "on_fail": "stop",
                    "max_retries": 1
                },
                {
                    "id": "script_retry",
                    "skill": "webtoon_script",
                    "condition": "_iteration > 1",
                    "inputs": {
                        "plot_points": "${context.plot_points}",
                        "chapters_text": "${context.chapters_text}",
                        "adapt_method": "${context.adapt_method}",
                        "episode_number": "${context.episode_number}",
                        "previous_script": "${script_result.full_script}",
                        "qa_feedback": "${qa_result}"
                    },
                    "output_key": "script_result",
                    "on_fail": "stop",
                    "max_retries": 1
                },
                {
                    "id": "qa",
                    "skill": "webtoon_aligner",
                    "inputs": {
                        "script": "${script_result.full_script}",
                        "chapters_text": "${context.chapters_text}",
                        "adapt_method": "${context.adapt_method}"
                    },
                    "output_key": "qa_result",
                    "on_fail": "skip",
                    "max_retries": 0
                }
            ]
        }
    }
]


# ==================== 初始化函数 ====================

async def init_simple_system(db: Session):
    """初始化简化的 Skill & Agent 系统"""

    # 1. 初始化内置 Skills
    print("初始化内置 Skills...")
    for skill_data in BUILTIN_SKILLS:
        # 检查是否已存在
        result = await db.execute(
            select(Skill).where(Skill.name == skill_data["name"])
        )
        existing_skill = result.scalar_one_or_none()

        if not existing_skill:
            # 创建新的 Skill
            skill = Skill(
                id=uuid.uuid4(),
                name=skill_data["name"],
                display_name=skill_data["display_name"],
                description=skill_data["description"],
                category=skill_data["category"],
                is_template_based=True,
                system_prompt=skill_data.get("system_prompt"),
                prompt_template=skill_data["prompt_template"],
                input_schema=skill_data["input_schema"],
                output_schema=skill_data["output_schema"],
                model_config=skill_data["model_config"],
                example_input=skill_data.get("example_input"),
                example_output=skill_data.get("example_output"),
                visibility="public",
                owner_id=SYSTEM_OWNER_ID,
                is_active=True,
                is_builtin=True,
                # 兼容旧字段
                module_path="app.ai.simple_executor",
                class_name="SimpleSkillExecutor"
            )
            db.add(skill)
            print(f"  ✓ 创建 Skill: {skill_data['display_name']}")
        else:
            # 更新已存在的内置 Skill
            existing_skill.display_name = skill_data["display_name"]
            existing_skill.description = skill_data["description"]
            existing_skill.system_prompt = skill_data.get("system_prompt")
            existing_skill.prompt_template = skill_data["prompt_template"]
            existing_skill.input_schema = skill_data["input_schema"]
            existing_skill.output_schema = skill_data["output_schema"]
            existing_skill.model_config = skill_data["model_config"]
            existing_skill.updated_at = datetime.utcnow()  # 使用 timezone-naive datetime
            print(f"  ↻ 更新 Skill: {skill_data['display_name']}")

    await db.commit()
    print(f"✓ 已初始化 {len(BUILTIN_SKILLS)} 个内置 Skills")

    # 2. 初始化内置 Agents
    print("\n初始化内置 Agents...")
    for agent_data in BUILTIN_AGENTS:
        # 检查是否已存在
        result = await db.execute(
            select(SimpleAgent).where(SimpleAgent.name == agent_data["name"])
        )
        existing_agent = result.scalar_one_or_none()

        if not existing_agent:
            # 创建新的 Agent
            agent = SimpleAgent(
                id=uuid.uuid4(),
                name=agent_data["name"],
                display_name=agent_data["display_name"],
                description=agent_data["description"],
                category=agent_data["category"],
                workflow=agent_data["workflow"],
                visibility="public",
                owner_id=SYSTEM_OWNER_ID,
                is_active=True,
                is_builtin=True
            )
            db.add(agent)
            print(f"  ✓ 创建 Agent: {agent_data['display_name']}")
        else:
            # 更新已存在的内置 Agent
            existing_agent.display_name = agent_data["display_name"]
            existing_agent.description = agent_data["description"]
            existing_agent.workflow = agent_data["workflow"]
            existing_agent.updated_at = datetime.utcnow()  # 使用 timezone-naive datetime
            print(f"  ↻ 更新 Agent: {agent_data['display_name']}")

    await db.commit()
    print(f"✓ 已初始化 {len(BUILTIN_AGENTS)} 个内置 Agents")

    print("\n✅ 简化系统初始化完成！")
