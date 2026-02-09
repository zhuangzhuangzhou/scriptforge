# 计划：剧集拆解(Plot)模块 - 基于可配置方法论系统

## 背景 (Context)

当前系统已具备：
- ✅ **配置系统**: `AIConfiguration` 模型 + `/api/v1/configurations` API + `AIConfigurationModal` 前端页面
- ✅ **基础拆解**: PlotBreakdown模型、Breakdown API、Celery异步任务
- ✅ **用户级覆盖**: 支持系统默认配置（user_id=NULL）和用户自定义配置（user_id=用户ID）
- ✅ **配置克隆**: 前端支持从系统配置克隆到用户配置

**缺失部分**：
- ❌ `docs/ai_flow_desc/` 下的方法论文档尚未导入配置系统
- ❌ 拆解/剧本生成时无法指定配置
- ❌ Skills 执行时无法动态读取配置

**核心方法论文档**（位于 `/docs/ai_flow_desc/`）：
- `webtoon-skill/adapt-method.md` (1435行): 冲突提取⭐⭐⭐/⭐⭐/⭐、情绪钩子10-6分评分、5种压缩策略
- `breakdown-aligner.md` (295行): 8维度质检标准（冲突强度、情绪钩子、密度、分集、压缩、描述、还原、类型）
- `webtoon-skill/output-style.md` (348行): 起承转钩结构、视觉化优先、快节奏风格

## 目标 (Goal)

1. **方法论配置化**: 将AI工作流文档导入 `AIConfiguration` 表，作为系统默认配置
2. **可选配置机制**: 拆解/剧本生成时可指定配置Key，Skills动态读取
3. **用户自定义**: 用户可克隆系统配置并修改（如调整冲突评分标准、情绪阈值）
4. **UI选择器**: 在启动拆解时提供配置选择界面

---

## 核心设计

### 📐 配置驱动架构

```
用户选择配置 (Frontend: ConfigSelector)
    ↓
API 接收配置Key (BreakdownStartRequest.config_key)
    ↓
AITask 保存配置Key (AITask.config["config_key"])
    ↓
Pipeline Executor 读取配置 (configService.getConfiguration)
    ↓
Skills 使用配置执行 (adapt_method + quality_rule)
    ↓
质检器应用规则 (BreakdownAligner)
    ↓
保存结果 (PlotBreakdown.used_adapt_method_id)
```

---

## 实施步骤

### 第一阶段：方法论文档解析与导入

#### 1.1 创建配置导入脚本

**文件**: `backend/scripts/init_breakdown_configs.py`

**任务**: 解析 `docs/ai_flow_desc/` 下的 Markdown 文档，提取结构化配置

**核心逻辑**:

```python
import re
import json
from pathlib import Path
from sqlalchemy.orm import Session
from app.models.ai_configuration import AIConfiguration

def parse_adapt_method(file_path: str) -> dict:
    """解析 adapt-method.md，提取改编方法论"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    return {
        "conflict_levels": {
            "core": {"symbol": "⭐⭐⭐", "desc": "改变主角命运、大幅改变格局", "keywords": ["改变命运", "生死", "身份揭露", "大战", "背叛"]},
            "secondary": {"symbol": "⭐⭐", "desc": "推进支线或铺垫", "keywords": ["误会", "竞争", "考验", "追踪"]},
            "transition": {"symbol": "⭐", "desc": "日常、铺垫、环境描写", "keywords": ["日常", "环境", "铺垫"]}
        },
        "emotion_hooks": {
            "scoring_guide": {
                "10": "让观众'卧槽'的时刻（必须单独成集）",
                "8-9": "让观众爽/虐/急的高潮（核心爽点）",
                "6-7": "让观众有感觉的时刻（可保留）",
                "4-5": "情绪平淡（应删除）"
            },
            "types": ["打脸蓄力", "碾压爽点", "金手指觉醒", "虐心痛点", "真相揭露", "身份反转", "反杀逆袭"],
            "min_score": 6  # 最低保留分数
        },
        "compression_strategies": [
            "删除过程，保留结果",
            "删除铺垫，爽点前置",
            "心理→动作，叙述→画面",
            "长对话→短对话（≤20字）",
            "升级蒙太奇快速完成"
        ],
        "episode_structure": {
            "pattern": "起承转钩",
            "word_count": {"min": 500, "max": 800},
            "duration": {"min": 60, "max": 120}  # 秒
        }
    }

def parse_breakdown_aligner(file_path: str) -> dict:
    """解析 breakdown-aligner.md，提取质检规则"""
    return {
        "dimensions": [
            {"name": "冲突强度评估", "weight": 0.15, "desc": "判断提取的冲突是否达到核心冲突标准"},
            {"name": "情绪钩子识别准确性", "weight": 0.15, "desc": "验证情绪钩子类型和强度评分是否准确"},
            {"name": "冲突密度达标性", "weight": 0.15, "desc": "计算6章内核心冲突数量"},
            {"name": "分集标注合理性", "weight": 0.15, "desc": "验证每集分配的剧情点数量"},
            {"name": "压缩策略正确性", "weight": 0.10, "desc": "验证该删的删了、该保留的保留了"},
            {"name": "剧情点描述规范", "weight": 0.10, "desc": "验证【剧情n】格式是否完整清晰"},
            {"name": "原文还原准确性", "weight": 0.10, "desc": "对比小说原文验证准确性"},
            {"name": "类型特性符合度", "weight": 0.10, "desc": "验证是否符合该小说类型特殊要求"}
        ],
        "pass_threshold": 0.80,
        "density_thresholds": {
            "high": {"min_core_conflicts": 5, "desc": "6章有5+个核心冲突"},
            "medium": {"min_core_conflicts": 2, "desc": "6章有2-4个核心冲突"},
            "low": {"min_core_conflicts": 0, "desc": "6章有0-1个核心冲突（需说明）"}
        }
    }

def parse_output_style(file_path: str) -> dict:
    """解析 output-style.md，提取输出风格规范"""
    return {
        "principles": [
            "视觉化优先：一切为画面服务",
            "节奏极快：瞬间进冲突，无废话",
            "情绪钩子密集：每集必有打脸/反转/碾压",
            "冲突可视化：力量对比用画面展示",
            "对话简短有力：冲突3句话，反击1句话"
        ],
        "structure": {
            "formula": "起承转钩",
            "stages": {
                "起": "瞬间进入冲突画面，不要铺垫",
                "承": "推进发展，展示对立",
                "转": "反转高潮，情绪爆发",
                "钩": "悬念结尾，观众欲罢不能"
            }
        },
        "constraints": {
            "dialogue_max_chars": 20,
            "scene_per_episode": {"min": 1, "max": 3},
            "dialogue_ratio": 0.35,  # 对话占30-40%
            "action_ratio": 0.45     # 动作占40-50%
        }
    }

def main():
    db = SessionLocal()
    try:
        base_path = Path("docs/ai_flow_desc")

        # 1. 导入适配方法
        adapt_method_data = parse_adapt_method(base_path / "webtoon-skill/adapt-method.md")
        adapt_config = AIConfiguration(
            key="adapt_method_default",
            category="adapt_method",
            value=adapt_method_data,
            description="网文改编漫剧方法论（系统默认）- 冲突提取、情绪钩子、压缩策略",
            user_id=None,
            is_active=True
        )
        db.merge(adapt_config)  # merge 支持幂等操作

        # 2. 导入质检规则
        qa_data = parse_breakdown_aligner(base_path / "breakdown-aligner.md")
        qa_config = AIConfiguration(
            key="qa_breakdown_default",
            category="quality_rule",
            value=qa_data,
            description="剧情拆解质检标准（系统默认）- 8维度质量检查",
            user_id=None,
            is_active=True
        )
        db.merge(qa_config)

        # 3. 导入输出风格
        style_data = parse_output_style(base_path / "webtoon-skill/output-style.md")
        style_config = AIConfiguration(
            key="output_style_default",
            category="prompt_template",
            value=style_data,
            description="漫剧输出风格（系统默认）- 起承转钩、视觉化优先",
            user_id=None,
            is_active=True
        )
        db.merge(style_config)

        db.commit()
        print("✅ 配置导入成功！")

    finally:
        db.close()

if __name__ == "__main__":
    main()
```

**执行**: `python backend/scripts/init_breakdown_configs.py`

---

### 第二阶段：API 增强 - 支持配置选择

#### 2.1 修改 Breakdown API

**文件**: `backend/app/api/v1/breakdown.py`

**修改点**: 在 `BreakdownStartRequest` 中增加配置选择字段

```python
class BreakdownStartRequest(BaseModel):
    """启动拆解请求"""
    batch_id: str
    model_config_id: Optional[str] = None
    selected_skills: Optional[List[str]] = None
    pipeline_id: Optional[str] = None
    # 新增字段
    adapt_method_key: Optional[str] = "adapt_method_default"  # 适配方法配置Key
    quality_rule_key: Optional[str] = "qa_breakdown_default"  # 质检规则配置Key
    output_style_key: Optional[str] = "output_style_default"  # 输出风格配置Key

@router.post("/start")
async def start_breakdown(
    request: BreakdownStartRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """启动剧情拆解"""
    # ... 现有验证逻辑 ...

    # 创建AI任务（保存配置Key）
    task = AITask(
        project_id=batch.project_id,
        batch_id=batch.id,
        task_type="breakdown",
        status="queued",
        depends_on=[],
        config={
            "model_config_id": request.model_config_id,
            "selected_skills": request.selected_skills or [],
            "pipeline_id": request.pipeline_id,
            # 保存配置Key供后续使用
            "adapt_method_key": request.adapt_method_key,
            "quality_rule_key": request.quality_rule_key,
            "output_style_key": request.output_style_key
        }
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)

    # 启动Celery异步任务
    celery_task = run_breakdown_task.delay(
        str(task.id),
        str(batch.id),
        str(batch.project_id),
        str(current_user.id)
    )

    task.celery_task_id = celery_task.id
    await db.commit()

    return {"task_id": str(task.id), "status": "queued"}
```

#### 2.2 新增配置查询辅助端点

```python
@router.get("/available-configs")
async def get_available_configs(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取拆解可用的配置列表"""
    from app.api.v1.configurations import list_configurations

    # 获取合并后的配置（用户覆盖系统默认）
    all_configs = await list_configurations(category=None, merge=True, db=db, current_user=current_user)

    # 按分类分组
    adapt_methods = [c for c in all_configs if c.category == "adapt_method"]
    quality_rules = [c for c in all_configs if c.category == "quality_rule"]
    output_styles = [c for c in all_configs if c.category == "prompt_template" and "output_style" in c.key]

    return {
        "adapt_methods": [{"key": c.key, "description": c.description} for c in adapt_methods],
        "quality_rules": [{"key": c.key, "description": c.description} for c in quality_rules],
        "output_styles": [{"key": c.key, "description": c.description} for c in output_styles]
    }
```

---

### 第三阶段：Skills 集成配置系统

#### 3.1 修改 Pipeline Executor - 读取配置

**文件**: `backend/app/ai/pipeline_executor.py`

**修改点**: 在初始化时读取任务配置中的配置Key

```python
class PipelineExecutor:
    def __init__(self, db: AsyncSession, model_adapter, user_id: str, task_config: dict = None):
        self.db = db
        self.model_adapter = model_adapter
        self.user_id = user_id
        self.task_config = task_config or {}
        # 缓存配置
        self._adapt_method = None
        self._quality_rule = None
        self._output_style = None

    async def get_adapt_method(self) -> dict:
        """获取适配方法配置（优先用户自定义）"""
        if self._adapt_method is None:
            key = self.task_config.get("adapt_method_key", "adapt_method_default")
            config = await self._load_config(key)
            self._adapt_method = config.value
        return self._adapt_method

    async def get_quality_rule(self) -> dict:
        """获取质检规则配置"""
        if self._quality_rule is None:
            key = self.task_config.get("quality_rule_key", "qa_breakdown_default")
            config = await self._load_config(key)
            self._quality_rule = config.value
        return self._quality_rule

    async def get_output_style(self) -> dict:
        """获取输出风格配置"""
        if self._output_style is None:
            key = self.task_config.get("output_style_key", "output_style_default")
            config = await self._load_config(key)
            self._output_style = config.value
        return self._output_style

    async def _load_config(self, key: str) -> AIConfiguration:
        """加载配置（用户自定义优先）"""
        result = await self.db.execute(
            select(AIConfiguration)
            .where(AIConfiguration.key == key)
            .where((AIConfiguration.user_id == self.user_id) | (AIConfiguration.user_id == None))
            .order_by(AIConfiguration.user_id.desc().nulls_last())
            .limit(1)
        )
        config = result.scalar_one_or_none()
        if not config:
            raise ValueError(f"配置不存在: {key}")
        return config
```

#### 3.2 Breakdown Skills 使用配置

**文件**: `backend/app/skills/breakdown/conflict_extractor.py`

```python
from app.skills.base import BaseSkill

class ConflictExtractorSkill(BaseSkill):
    """冲突点提取Skill - 基于用户选择的适配方法"""

    async def execute(self, context: dict) -> dict:
        chapters = context.get("chapters", [])
        # 从 Pipeline Executor 获取配置
        adapt_method = context.get("adapt_method")
        if not adapt_method:
            raise ValueError("缺少 adapt_method 配置")

        conflict_levels = adapt_method["conflict_levels"]

        conflicts = []
        for chapter in chapters:
            # 构建包含配置的 Prompt
            prompt = self.build_extraction_prompt(chapter, conflict_levels)

            # 调用AI提取冲突
            result = await self.model_adapter.generate(
                prompt=prompt,
                temperature=0.7
            )

            # 解析并分级
            chapter_conflicts = self.parse_and_classify(result, conflict_levels)
            conflicts.extend(chapter_conflicts)

        return {"conflicts": conflicts}

    def build_extraction_prompt(self, chapter: dict, levels: dict) -> str:
        """构建提取Prompt，注入分级标准"""
        return f"""
从以下章节中提取冲突点，并按以下标准分级：

- ⭐⭐⭐ 核心冲突: {levels["core"]["desc"]}
  关键词: {", ".join(levels["core"]["keywords"])}

- ⭐⭐ 次级冲突: {levels["secondary"]["desc"]}
  关键词: {", ".join(levels["secondary"]["keywords"])}

- ⭐ 过渡冲突: {levels["transition"]["desc"]}

章节内容：
{chapter["content"]}

请以JSON数组格式返回，每个冲突包含：
- title: 冲突标题
- description: 冲突描述
- type: 冲突类型（人物对立/力量对比/身份矛盾/情感纠葛/生存危机/真相悬念）
- level: ⭐⭐⭐ / ⭐⭐ / ⭐
"""

    def parse_and_classify(self, ai_result: str, levels: dict) -> list:
        """解析AI返回并二次验证分级"""
        import json
        conflicts = json.loads(ai_result)

        # 二次验证分级（基于关键词）
        for conflict in conflicts:
            desc = conflict.get("description", "")
            auto_level = self._classify_by_keywords(desc, levels)

            # 如果AI分级与关键词分级不一致，取较低等级（保守策略）
            if auto_level != conflict["level"]:
                conflict["level"] = min(auto_level, conflict["level"], key=lambda x: x.count("⭐"))

        return conflicts

    def _classify_by_keywords(self, text: str, levels: dict) -> str:
        """基于关键词自动分级"""
        if any(kw in text for kw in levels["core"]["keywords"]):
            return "⭐⭐⭐"
        elif any(kw in text for kw in levels["secondary"]["keywords"]):
            return "⭐⭐"
        else:
            return "⭐"
```

#### 3.3 质检器集成配置

**文件**: `backend/app/ai/validators/breakdown_aligner.py`

```python
class BreakdownAligner:
    """剧情拆解质量校验器"""

    def __init__(self, db: AsyncSession, quality_rule: dict, adapt_method: dict):
        self.db = db
        self.quality_rule = quality_rule
        self.adapt_method = adapt_method

    async def validate(self, breakdown_data: dict, chapters: list) -> dict:
        """执行8维度质检"""
        dimensions = self.quality_rule["dimensions"]
        pass_threshold = self.quality_rule["pass_threshold"]

        results = []
        total_score = 0.0

        for dim in dimensions:
            score = await self._check_dimension(dim["name"], breakdown_data, chapters)
            weighted_score = score * dim["weight"]
            total_score += weighted_score

            results.append({
                "dimension": dim["name"],
                "score": score,
                "weight": dim["weight"],
                "weighted_score": weighted_score,
                "status": "PASS" if score >= 0.8 else "FAIL",
                "desc": dim["desc"]
            })

        return {
            "status": "PASS" if total_score >= pass_threshold else "FAIL",
            "total_score": total_score,
            "pass_threshold": pass_threshold,
            "details": results
        }

    async def _check_dimension(self, dimension: str, data: dict, chapters: list) -> float:
        """检查单个维度"""
        if dimension == "冲突密度达标性":
            return self._check_conflict_density(data["conflicts"], len(chapters))
        elif dimension == "情绪钩子识别准确性":
            return self._check_emotion_hooks(data["plot_hooks"])
        # ... 其他维度

    def _check_conflict_density(self, conflicts: list, chapter_count: int) -> float:
        """冲突密度检查 - 使用配置中的阈值"""
        thresholds = self.quality_rule.get("density_thresholds", {})
        core_conflicts = [c for c in conflicts if c["level"] == "⭐⭐⭐"]
        count = len(core_conflicts)

        if count >= thresholds.get("high", {}).get("min_core_conflicts", 5):
            return 1.0
        elif count >= thresholds.get("medium", {}).get("min_core_conflicts", 2):
            return 0.85
        else:
            return 0.6

    def _check_emotion_hooks(self, hooks: list) -> float:
        """情绪钩子检查 - 使用配置中的最低分数"""
        min_score = self.adapt_method["emotion_hooks"].get("min_score", 6)
        valid_hooks = [h for h in hooks if h.get("score", 0) >= min_score]
        ratio = len(valid_hooks) / max(len(hooks), 1)
        return ratio
```

---

### 第四阶段：Celery 任务集成配置

**文件**: `backend/app/tasks/breakdown_tasks.py`

**修改点**: 传递任务配置给 PipelineExecutor

```python
@celery_app.task(bind=True)
def run_breakdown_task(self, task_id: str, batch_id: str, project_id: str, user_id: str):
    """执行Breakdown任务"""

    async def _run():
        async with AsyncSessionLocal() as db:
            try:
                # 读取任务配置
                task_result = await db.execute(select(AITask).where(AITask.id == task_id))
                task_record = task_result.scalar_one()
                task_config = task_record.config  # 包含 adapt_method_key 等配置

                # 创建 Pipeline Executor（传入配置）
                model_adapter = await get_adapter()
                executor = PipelineExecutor(db, model_adapter, user_id, task_config=task_config)

                # 加载配置并注入到上下文
                adapt_method = await executor.get_adapt_method()
                quality_rule = await executor.get_quality_rule()
                output_style = await executor.get_output_style()

                # 执行拆解（配置会传递给所有Skills）
                await executor.run_breakdown(
                    project_id, batch_id,
                    pipeline_id=task_config.get("pipeline_id"),
                    selected_skills=task_config.get("selected_skills"),
                    progress_callback=progress_callback,
                    # 注入配置
                    context_overrides={
                        "adapt_method": adapt_method,
                        "quality_rule": quality_rule,
                        "output_style": output_style
                    }
                )

                # 任务完成，保存使用的配置Key
                breakdown = await get_breakdown_by_batch(db, batch_id)
                breakdown.used_adapt_method_id = task_config.get("adapt_method_key")
                await db.commit()

            except Exception as e:
                # 错误处理...
                raise

    return asyncio.run(_run())
```

**修改 PipelineExecutor.run_breakdown()**:

```python
async def run_breakdown(
    self,
    project_id,
    batch_id,
    pipeline_id,
    selected_skills,
    progress_callback,
    context_overrides: dict = None
):
    # 初始化上下文
    context = {
        "chapters": await self._load_chapters(batch_id),
        "model_adapter": self.model_adapter,
        **(context_overrides or {})  # 注入配置
    }

    # 执行 Skills（配置已在上下文中）
    context = await self._execute_skills(skills, context, progress_callback)

    # 质检（使用配置中的规则）
    aligner = BreakdownAligner(
        self.db,
        quality_rule=context["quality_rule"],
        adapt_method=context["adapt_method"]
    )
    validation = await aligner.validate(context, context["chapters"])

    # 保存结果...
```

---

### 第五阶段：前端 UI 实现

#### 5.1 配置选择器组件

**文件**: `frontend/src/components/ConfigSelector.tsx` (新建)

```tsx
import React, { useState, useEffect } from 'react';
import { Select, Spin, Tag, Tooltip } from 'antd';
import { InfoCircleOutlined } from '@ant-design/icons';
import { GlassSelect } from './ui/GlassSelect';
import { breakdownApi } from '../services/api';

interface ConfigSelectorProps {
  value?: {
    adapt_method_key?: string;
    quality_rule_key?: string;
    output_style_key?: string;
  };
  onChange?: (value: any) => void;
}

const ConfigSelector: React.FC<ConfigSelectorProps> = ({ value = {}, onChange }) => {
  const [loading, setLoading] = useState(false);
  const [configs, setConfigs] = useState<any>({
    adapt_methods: [],
    quality_rules: [],
    output_styles: []
  });

  useEffect(() => {
    loadConfigs();
  }, []);

  const loadConfigs = async () => {
    setLoading(true);
    try {
      const data = await breakdownApi.getAvailableConfigs();
      setConfigs(data);
    } catch (error) {
      console.error('加载配置失败', error);
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (field: string, val: string) => {
    const newValue = { ...value, [field]: val };
    onChange?.(newValue);
  };

  if (loading) return <Spin />;

  return (
    <div className="space-y-4">
      <div>
        <label className="text-slate-300 text-sm flex items-center gap-2 mb-2">
          适配方法 (Adapt Method)
          <Tooltip title="决定如何提取冲突、识别情绪钩子、应用压缩策略">
            <InfoCircleOutlined className="text-slate-500" />
          </Tooltip>
        </label>
        <GlassSelect
          value={value.adapt_method_key || 'adapt_method_default'}
          onChange={(val) => handleChange('adapt_method_key', val)}
          className="w-full"
        >
          {configs.adapt_methods.map((cfg: any) => (
            <Select.Option key={cfg.key} value={cfg.key}>
              <div className="flex items-center justify-between">
                <span className="font-mono text-sm">{cfg.key}</span>
                {cfg.key.includes('default') && <Tag color="blue">系统默认</Tag>}
              </div>
              <div className="text-xs text-slate-400 mt-1">{cfg.description}</div>
            </Select.Option>
          ))}
        </GlassSelect>
      </div>

      <div>
        <label className="text-slate-300 text-sm flex items-center gap-2 mb-2">
          质检规则 (Quality Rule)
          <Tooltip title="8维度质量检查标准，决定拆解结果的通过阈值">
            <InfoCircleOutlined className="text-slate-500" />
          </Tooltip>
        </label>
        <GlassSelect
          value={value.quality_rule_key || 'qa_breakdown_default'}
          onChange={(val) => handleChange('quality_rule_key', val)}
          className="w-full"
        >
          {configs.quality_rules.map((cfg: any) => (
            <Select.Option key={cfg.key} value={cfg.key}>
              <div className="flex items-center justify-between">
                <span className="font-mono text-sm">{cfg.key}</span>
                {cfg.key.includes('default') && <Tag color="cyan">系统默认</Tag>}
              </div>
              <div className="text-xs text-slate-400 mt-1">{cfg.description}</div>
            </Select.Option>
          ))}
        </GlassSelect>
      </div>

      <div>
        <label className="text-slate-300 text-sm flex items-center gap-2 mb-2">
          输出风格 (Output Style)
          <Tooltip title="剧本输出的风格规范（起承转钩、视觉化优先）">
            <InfoCircleOutlined className="text-slate-500" />
          </Tooltip>
        </label>
        <GlassSelect
          value={value.output_style_key || 'output_style_default'}
          onChange={(val) => handleChange('output_style_key', val)}
          className="w-full"
        >
          {configs.output_styles.map((cfg: any) => (
            <Select.Option key={cfg.key} value={cfg.key}>
              <div className="flex items-center justify-between">
                <span className="font-mono text-sm">{cfg.key}</span>
                {cfg.key.includes('default') && <Tag color="purple">系统默认</Tag>}
              </div>
              <div className="text-xs text-slate-400 mt-1">{cfg.description}</div>
            </Select.Option>
          ))}
        </GlassSelect>
      </div>
    </div>
  );
};

export default ConfigSelector;
```

#### 5.2 拆解配置弹窗集成

**文件**: `frontend/src/pages/user/Workspace.tsx`

**修改点**: 在 PLOT Tab 中集成 ConfigSelector

```tsx
import ConfigSelector from '../../components/ConfigSelector';

// 在组件状态中添加
const [breakdownConfig, setBreakdownConfig] = useState({
  adapt_method_key: 'adapt_method_default',
  quality_rule_key: 'qa_breakdown_default',
  output_style_key: 'output_style_default'
});

// 拆解配置弹窗
const BreakdownConfigModal = () => (
  <GlassModal
    title="配置剧情拆解参数"
    visible={isBreakdownModalOpen}
    onOk={handleStartBreakdownWithConfig}
    onCancel={() => setIsBreakdownModalOpen(false)}
    width={700}
  >
    <div className="space-y-6">
      {/* Skill 选择器（已有）*/}
      <div>
        <h3 className="text-white mb-3">选择拆解技能</h3>
        <SkillSelector
          category="breakdown"
          selectedSkills={selectedBreakdownSkills}
          onChange={setSelectedBreakdownSkills}
        />
      </div>

      {/* 配置选择器（新增）*/}
      <div>
        <h3 className="text-white mb-3">选择改编方法与质检规则</h3>
        <ConfigSelector
          value={breakdownConfig}
          onChange={setBreakdownConfig}
        />
      </div>
    </div>
  </GlassModal>
);

// 启动拆解时传递配置
const handleStartBreakdownWithConfig = async () => {
  try {
    const response = await breakdownApi.start({
      batch_id: targetBatchId,
      selected_skills: selectedBreakdownSkills,
      // 传递配置
      adapt_method_key: breakdownConfig.adapt_method_key,
      quality_rule_key: breakdownConfig.quality_rule_key,
      output_style_key: breakdownConfig.output_style_key
    });

    message.success('拆解任务已启动');
    setIsBreakdownModalOpen(false);
    // 开始监听任务进度...
  } catch (error) {
    message.error('启动失败');
  }
};
```

#### 5.3 升级 AIConfigurationModal - 添加快捷入口

**文件**: `frontend/src/components/modals/AIConfigurationModal.tsx`

**新增功能**: 在模态框顶部添加提示信息

```tsx
{/* 在模态框 Content 开头添加 */}
<div className="bg-blue-900/20 border border-blue-700/30 rounded-lg p-4 mb-6">
  <div className="flex items-start gap-3">
    <InfoCircleOutlined className="text-blue-400 text-lg mt-0.5" />
    <div>
      <h4 className="text-blue-300 font-bold mb-1">配置使用说明</h4>
      <ul className="text-sm text-slate-300 space-y-1">
        <li>• 系统默认配置：所有用户共享，不可编辑</li>
        <li>• 自定义配置：点击"自定义此配置"克隆后可编辑，保存后在拆解时可选择使用</li>
        <li>• 配置优先级：启动拆解时指定的配置 > 用户自定义配置 > 系统默认配置</li>
      </ul>
    </div>
  </div>
</div>
```

---

### 第六阶段：API Service 层增强

**文件**: `frontend/src/services/api.ts`

**新增方法**:

```typescript
export const breakdownApi = {
  // 已有方法...

  // 新增：获取可用配置列表
  async getAvailableConfigs() {
    const response = await apiClient.get('/api/v1/breakdown/available-configs');
    return response.data;
  },

  // 修改：启动拆解（支持配置参数）
  async start(params: {
    batch_id: string;
    selected_skills?: string[];
    adapt_method_key?: string;
    quality_rule_key?: string;
    output_style_key?: string;
  }) {
    const response = await apiClient.post('/api/v1/breakdown/start', params);
    return response.data;
  },

  // 新增：获取质检报告
  async getQAReport(batchId: string) {
    const response = await apiClient.get(`/api/v1/breakdown/qa-report/${batchId}`);
    return response.data;
  }
};
```

---

## 验证计划 (Verification)

### 1. 后端验证

```bash
# Step 1: 初始化配置
cd /Users/zhouqiang/Data/jim/backend
python scripts/init_breakdown_configs.py

# 验证配置写入
psql -d scriptflow -c "
  SELECT key, category, user_id, description
  FROM ai_configurations
  WHERE category IN ('adapt_method', 'quality_rule', 'prompt_template')
  ORDER BY category, user_id NULLS FIRST;
"

# 预期输出：
# - adapt_method_default (user_id=NULL)
# - qa_breakdown_default (user_id=NULL)
# - output_style_default (user_id=NULL)

# Step 2: 测试配置 API
curl -X GET http://localhost:8000/api/v1/configurations?merge=true \
  -H "Authorization: Bearer $TOKEN"

# Step 3: 测试启动拆解（带配置）
curl -X POST http://localhost:8000/api/v1/breakdown/start \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "batch_id": "xxx",
    "selected_skills": ["conflict_extractor"],
    "adapt_method_key": "adapt_method_default",
    "quality_rule_key": "qa_breakdown_default"
  }'

# Step 4: 查看任务配置是否正确保存
psql -d scriptflow -c "
  SELECT id, config->'adapt_method_key', config->'quality_rule_key'
  FROM ai_tasks
  WHERE task_type='breakdown'
  ORDER BY created_at DESC LIMIT 1;
"
```

### 2. 用户自定义配置验证

**场景**: 用户克隆系统配置并修改冲突评分标准

```bash
# Step 1: 在前端 AIConfigurationModal 中点击"自定义此配置"
# 克隆 adapt_method_default

# Step 2: 修改配置（降低核心冲突关键词阈值）
# 将 "改变命运" 修改为 "挑战"

# Step 3: 保存为用户自定义配置（key 保持 adapt_method_default）

# Step 4: 启动拆解时选择"我的配置"

# Step 5: 验证使用的是用户配置
curl http://localhost:8000/api/v1/configurations/adapt_method_default \
  -H "Authorization: Bearer $TOKEN"

# 预期：返回用户修改后的配置（user_id 为当前用户ID）
```

### 3. 前端集成验证

**场景 1**: 启动拆解选择配置
1. 进入 Workspace PLOT Tab
2. 点击批次卡片的"启动拆解"按钮
3. 弹窗显示：
   - Skill 选择器（已有）
   - **配置选择器（新增）**：
     - 适配方法下拉列表（系统默认 + 用户自定义）
     - 质检规则下拉列表
     - 输出风格下拉列表
4. 选择配置后点击"保存配置并启动"
5. 观察 WebSocket 推送进度
6. 拆解完成后查看质检报告

**场景 2**: 管理配置
1. 点击 MainLayout 顶部 Bot 图标
2. 进入 AIConfigurationModal
3. 切换到"系统默认配置" Tab
4. 点击 `adapt_method_default` 的"自定义此配置"按钮
5. 弹出编辑器，显示完整的 JSON 配置
6. 修改 `emotion_hooks.min_score` 从 6 改为 7
7. 保存
8. 切换到"我的配置" Tab，确认新配置出现
9. 下次启动拆解时，配置下拉列表中应显示该自定义配置

**场景 3**: 质检报告查看
1. 拆解完成后，批次卡片显示质检分数（如 85分）
2. 点击"查看质检"按钮
3. 弹窗显示：
   - 总分：85/100
   - 通过状态：PASS
   - 8个维度详细评分（每个维度显示权重、得分、状态）
   - 使用的配置：adapt_method_default (系统默认)

---

## 关键文件清单

### 新建文件

**后端**:
- `backend/scripts/init_breakdown_configs.py` - 配置初始化脚本
- `backend/app/skills/breakdown/conflict_extractor.py` - 冲突提取 Skill
- `backend/app/skills/breakdown/emotion_hook_analyzer.py` - 情绪钩子 Skill
- `backend/app/ai/validators/breakdown_aligner.py` - 质检系统

**前端**:
- `frontend/src/components/ConfigSelector.tsx` - 配置选择器组件

### 修改文件

**后端**:
- `backend/app/api/v1/breakdown.py` - API 增强（新增字段、端点）
- `backend/app/ai/pipeline_executor.py` - 集成配置读取
- `backend/app/tasks/breakdown_tasks.py` - 传递配置给 Executor

**前端**:
- `frontend/src/pages/user/Workspace.tsx` - PLOT Tab 集成 ConfigSelector
- `frontend/src/components/modals/AIConfigurationModal.tsx` - 添加使用说明
- `frontend/src/services/api.ts` - 新增 API 方法

### 已有文件（复用）

- `backend/app/models/ai_configuration.py` - AI 配置模型（已有）
- `backend/app/api/v1/configurations.py` - 配置 API（已有）
- `frontend/src/components/modals/AIConfigurationModal.tsx` - 配置管理界面（已有）
- `frontend/src/components/SkillSelector.tsx` - Skill 选择器（已有）

### 数据文件（源）

- `/docs/ai_flow_desc/webtoon-skill/adapt-method.md` - 方法论源文档
- `/docs/ai_flow_desc/breakdown-aligner.md` - 质检标准源文档
- `/docs/ai_flow_desc/webtoon-skill/output-style.md` - 输出风格源文档

---

## 依赖资源

### 已实现模块
- ✅ `AIConfiguration` 模型 + API + 前端管理界面
- ✅ PlotBreakdown 模型
- ✅ Breakdown API (`/api/v1/breakdown/start`, `/api/v1/breakdown/results`)
- ✅ Celery 任务 (`run_breakdown_task`)
- ✅ WebSocket 推送 (`/api/v1/websocket/ws/breakdown/{task_id}`)
- ✅ Skill 系统（Skill 模型、SkillSelector 组件）
- ✅ Glass UI 组件库

### 待实现模块
- ❌ 配置初始化脚本
- ❌ Breakdown Skills（冲突提取、情绪钩子分析）
- ❌ BreakdownAligner 质检器
- ❌ ConfigSelector 组件
- ❌ API 增强（配置参数支持）

---

## 实施优先级

### P0 (核心功能 - 必须实现)
1. **配置初始化脚本** - 将方法论导入数据库
2. **API 增强** - 支持配置参数传递
3. **Pipeline Executor 集成** - 读取并使用配置
4. **ConfigSelector 组件** - 前端配置选择

### P1 (质量保障 - 强烈建议)
5. **Breakdown Skills** - 冲突提取、情绪钩子分析
6. **BreakdownAligner** - 8维度质检

### P2 (体验优化 - 可后续迭代)
7. **质检报告可视化** - 详细报告弹窗
8. **配置模板库** - 预设多种方法论模板
9. **配置版本管理** - 支持配置历史回滚

---

### 第五阶段：前端UI实现

#### 5.1 升级Workspace PLOT Tab

**文件**: `frontend/src/pages/user/Workspace.tsx`

**新增功能**:

1. **批次卡片增强**: 显示质检状态和分数
```tsx
<div className="bg-slate-900/40 border border-slate-800 rounded-xl p-4">
  <div className="flex justify-between items-start mb-3">
    <div>
      <h3 className="text-white font-bold">批次 {batch.batch_number}</h3>
      <p className="text-sm text-slate-400">第 {batch.start_chapter}-{batch.end_chapter} 章</p>
    </div>
    <Badge status={batch.breakdown_status} />
  </div>

  {/* 质检分数可视化 */}
  {batch.qa_report && (
    <div className="mt-3 pt-3 border-t border-slate-800">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs text-slate-400">质检总分</span>
        <span className="text-lg font-bold text-cyan-400">
          {(batch.qa_report.total_score * 100).toFixed(0)}分
        </span>
      </div>
      <Progress percent={batch.qa_report.total_score * 100} status={batch.qa_status === 'PASS' ? 'success' : 'exception'} />
    </div>
  )}

  {/* 操作按钮 */}
  <div className="flex gap-2 mt-4">
    <Button onClick={() => handleStartBreakdown(batch.id)}>
      启动拆解
    </Button>
    <Button onClick={() => handleViewQA(batch.id)}>
      查看质检
    </Button>
  </div>
</div>
```

2. **质检详情弹窗** (`QAReportModal.tsx`):
```tsx
<GlassModal title="质检报告" visible={qaModalVisible}>
  {qaReport.details.map(dim => (
    <div key={dim.dimension} className="mb-4">
      <div className="flex justify-between items-center mb-2">
        <span className="text-white">{dim.dimension}</span>
        <Badge
          status={dim.status}
          text={`${(dim.score * 100).toFixed(0)}分`}
        />
      </div>
      <Progress
        percent={dim.score * 100}
        strokeColor={dim.status === 'PASS' ? '#10b981' : '#ef4444'}
      />
    </div>
  ))}
</GlassModal>
```

3. **拆解配置弹窗** (`BreakdownConfigModal.tsx`):
```tsx
<GlassModal title="配置拆解参数" visible={configModalVisible}>
  {/* Skill选择器 */}
  <SkillSelector
    category="breakdown"
    selectedSkills={selectedBreakdownSkills}
    onChange={setSelectedBreakdownSkills}
  />

  {/* 适配方法选择 */}
  <GlassSelect
    label="适配方法"
    options={adaptMethods}
    value={selectedAdaptMethod}
    onChange={setSelectedAdaptMethod}
  />

  {/* Pipeline选择 */}
  <GlassSelect
    label="执行流水线"
    options={pipelines}
    value={selectedPipeline}
    onChange={setSelectedPipeline}
  />

  <Button onClick={handleSaveConfig}>保存配置并启动</Button>
</GlassModal>
```

#### 5.2 升级PlotBreakdown独立页面

**文件**: `frontend/src/pages/user/PlotBreakdown.tsx`

**新增功能**:

1. **冲突可视化时间轴**:
```tsx
<Timeline>
  {conflicts.map(conflict => (
    <Timeline.Item
      key={conflict.id}
      color={getConflictColor(conflict.level)}
      dot={<ConflictIcon level={conflict.level} />}
    >
      <div className="flex items-start gap-3">
        <Badge text={conflict.level} />
        <div>
          <h4 className="text-white font-bold">{conflict.title}</h4>
          <p className="text-slate-400 text-sm">{conflict.description}</p>
          <div className="flex gap-2 mt-2">
            <Tag>章节 {conflict.chapter_number}</Tag>
            <Tag>冲突类型: {conflict.type}</Tag>
          </div>
        </div>
      </div>
    </Timeline.Item>
  ))}
</Timeline>
```

2. **情绪钩子热力图**:
```tsx
<div className="grid grid-cols-10 gap-1">
  {emotionHooks.map(hook => (
    <div
      key={hook.id}
      className={`h-12 rounded ${getHeatColor(hook.score)}`}
      title={`${hook.title} - ${hook.score}分`}
    />
  ))}
</div>
```

3. **分集预览**:
```tsx
<GlassCard>
  <h3>分集标注预览</h3>
  {episodeMarkers.map(marker => (
    <div key={marker.episode_number} className="border-b border-slate-800 py-3">
      <div className="flex justify-between">
        <span className="text-cyan-400 font-bold">第 {marker.episode_number} 集</span>
        <span className="text-slate-400">{marker.plot_points.length} 个剧情点</span>
      </div>
      <p className="text-sm text-slate-300 mt-1">{marker.summary}</p>
    </div>
  ))}
</GlassCard>
```

---

### 第六阶段：WebSocket实时推送升级

**文件**: `backend/app/api/v1/websocket.py`

**增强消息格式**:

```python
progress_data = {
    "task_id": str(task.id),
    "status": task.status,
    "progress": task.progress or 0,
    "current_step": task.current_step or "",
    # 新增字段
    "breakdown_stats": {
        "conflicts_found": len(context.get("conflicts", [])),
        "hooks_found": len(context.get("plot_hooks", [])),
        "characters_found": len(context.get("characters", []))
    },
    "qa_preview": {
        "passed_dimensions": passed_count,
        "total_dimensions": 8,
        "current_score": current_score
    }
}
```

---

## 验证计划 (Verification)

### 1. 后端验证

```bash
# 初始化配置
python backend/scripts/init_breakdown_configs.py

# 验证配置写入
psql -d scriptflow -c "SELECT key, category FROM ai_configurations WHERE user_id IS NULL;"

# API测试
curl -X POST http://localhost:8000/api/v1/breakdown/start \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"batch_id": "xxx", "selected_skills": ["conflict_extractor", "emotion_hook_analyzer"]}'

# 查看质检报告
curl http://localhost:8000/api/v1/breakdown/qa-report/xxx
```

### 2. 质检系统验证

**测试用例**: 使用6章小说原文（包含3个核心冲突、5个高强度钩子）

**预期结果**:
- 冲突密度检查: PASS (3/6 = 中密度)
- 情绪钩子识别: PASS (5个高强度钩子)
- 总分: ≥80分
- qa_status: PASS

### 3. 前端验证

**场景1**: 启动拆解
1. 进入Workspace PLOT Tab
2. 点击"启动拆解"
3. 选择Skills和适配方法
4. 观察WebSocket实时推送进度
5. 拆解完成后查看质检分数和状态

**场景2**: 查看质检报告
1. 点击批次卡片的"查看质检"按钮
2. 弹窗显示8维度详细评分
3. 每个维度显示通过/失败状态
4. 总分以百分比形式展示

**场景3**: 可视化查看拆解结果
1. 进入PlotBreakdown独立页面
2. 时间轴展示所有冲突点（带⭐⭐⭐/⭐⭐/⭐标记）
3. 情绪钩子热力图（10-6分颜色渐变）
4. 分集标注预览列表

---

## 关键文件清单

### 后端
- `backend/scripts/init_breakdown_configs.py` - 配置初始化脚本
- `backend/app/skills/breakdown/conflict_extractor.py` - 冲突提取Skill
- `backend/app/skills/breakdown/emotion_hook_analyzer.py` - 情绪钩子Skill
- `backend/app/skills/breakdown/episode_marker.py` - 分集标注Skill
- `backend/app/ai/validators/breakdown_aligner.py` - 质检系统
- `backend/app/ai/pipeline_executor.py` - Pipeline执行器（修改）
- `backend/app/api/v1/breakdown.py` - API路由（新增端点）
- `backend/app/api/v1/websocket.py` - WebSocket推送（增强）

### 前端
- `frontend/src/pages/user/Workspace.tsx` - PLOT Tab增强
- `frontend/src/pages/user/PlotBreakdown.tsx` - 独立页面升级
- `frontend/src/components/modals/QAReportModal.tsx` - 质检报告弹窗（新建）
- `frontend/src/components/modals/BreakdownConfigModal.tsx` - 配置弹窗（新建）
- `frontend/src/components/ConflictTimeline.tsx` - 冲突时间轴组件（新建）
- `frontend/src/components/EmotionHeatmap.tsx` - 情绪热力图组件（新建）

### 配置
- `docs/ai_flow_desc/adapt-method.md` - 方法论源文档
- `docs/ai_flow_desc/breakdown-aligner.md` - 质检标准源文档

---

## 依赖资源

- **已有模型**: PlotBreakdown, Batch, AITask, Skill, AIConfiguration
- **已有API**: `/api/v1/breakdown/start`, `/api/v1/breakdown/results/{batch_id}`
- **已有组件**: SkillSelector, GlassModal, GlassCard, ConsoleLogger
- **AI方法论文档**: `/docs/ai_flow_desc/` 目录下所有文档
- **Celery任务**: `run_breakdown_task` (已实现)
- **WebSocket**: `/api/v1/websocket/ws/breakdown/{task_id}` (已实现)
