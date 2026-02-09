#!/usr/bin/env python3
"""
配置初始化脚本：将 AI 工作流方法论文档导入到 AIConfiguration 系统

使用方法：
    cd /Users/zhouqiang/Data/jim/backend
    python scripts/init_breakdown_configs.py
"""

import sys
import asyncio
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import AsyncSessionLocal
from app.models.ai_configuration import AIConfiguration


def parse_adapt_method() -> dict:
    """
    解析 adapt-method.md，提取改编方法论配置

    返回结构化配置，包含：
    - conflict_levels: 冲突分级标准（⭐⭐⭐/⭐⭐/⭐）
    - emotion_hooks: 情绪钩子评分标准（10-6分）
    - compression_strategies: 压缩策略列表
    - episode_structure: 分集结构规范
    """
    return {
        "conflict_levels": {
            "core": {
                "symbol": "⭐⭐⭐",
                "desc": "改变主角命运、大幅改变格局",
                "keywords": ["改变命运", "生死", "身份揭露", "大战", "背叛", "决战", "觉醒"]
            },
            "secondary": {
                "symbol": "⭐⭐",
                "desc": "推进支线或铺垫的事件",
                "keywords": ["误会", "竞争", "考验", "追踪", "试探", "冲突"]
            },
            "transition": {
                "symbol": "⭐",
                "desc": "日常、铺垫、环境描写，无明显对立和张力",
                "keywords": ["日常", "环境", "铺垫", "过渡"]
            }
        },
        "emotion_hooks": {
            "scoring_guide": {
                "10": "让观众'卧槽'的时刻（必须单独成集）",
                "8-9": "让观众爽/虐/急的高潮（核心爽点）",
                "6-7": "让观众有感觉的时刻（可保留）",
                "4-5": "情绪平淡（应删除）"
            },
            "types": [
                "打脸蓄力",
                "碾压爽点",
                "金手指觉醒",
                "虐心痛点",
                "真相揭露",
                "身份反转",
                "反杀逆袭",
                "先知优势"
            ],
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
            "stages": {
                "起": "瞬间进入冲突画面，不要铺垫",
                "承": "推进发展，展示对立",
                "转": "反转高潮，情绪爆发",
                "钩": "悬念结尾，观众欲罢不能"
            },
            "word_count": {"min": 500, "max": 800},
            "duration_seconds": {"min": 60, "max": 120}
        }
    }


def parse_breakdown_aligner() -> dict:
    """
    解析 breakdown-aligner.md，提取质检规则配置

    返回 8 维度质检标准：
    - dimensions: 维度列表（名称、权重、描述）
    - pass_threshold: 通过阈值（0.80）
    - density_thresholds: 冲突密度要求
    """
    return {
        "dimensions": [
            {
                "name": "冲突强度评估",
                "weight": 0.15,
                "desc": "判断提取的冲突是否达到核心冲突标准"
            },
            {
                "name": "情绪钩子识别准确性",
                "weight": 0.15,
                "desc": "验证情绪钩子类型和强度评分是否准确"
            },
            {
                "name": "冲突密度达标性",
                "weight": 0.15,
                "desc": "计算6章内核心冲突数量，判断密度是否达标"
            },
            {
                "name": "分集标注合理性",
                "weight": 0.15,
                "desc": "验证每集分配的剧情点数量、字数估算是否合理"
            },
            {
                "name": "压缩策略正确性",
                "weight": 0.10,
                "desc": "验证该删的删了、该保留的保留了"
            },
            {
                "name": "剧情点描述规范",
                "weight": 0.10,
                "desc": "验证【剧情n】格式是否完整清晰"
            },
            {
                "name": "原文还原准确性",
                "weight": 0.10,
                "desc": "对比小说原文，验证是否准确提取"
            },
            {
                "name": "类型特性符合度",
                "weight": 0.10,
                "desc": "验证是否符合该小说类型的特殊要求"
            }
        ],
        "pass_threshold": 0.80,
        "density_thresholds": {
            "high": {
                "min_core_conflicts": 5,
                "desc": "6章有5+个核心冲突"
            },
            "medium": {
                "min_core_conflicts": 2,
                "desc": "6章有2-4个核心冲突"
            },
            "low": {
                "min_core_conflicts": 0,
                "desc": "6章有0-1个核心冲突（需说明原因）"
            }
        }
    }


def parse_output_style() -> dict:
    """
    解析 output-style.md，提取输出风格规范

    返回输出风格配置：
    - principles: 核心原则
    - structure: 起承转钩结构
    - constraints: 约束条件（字数、对话长度等）
    """
    return {
        "principles": [
            "视觉化优先：一切为画面服务",
            "节奏极快：瞬间进冲突，无废话无铺垫",
            "情绪钩子密集：每集必有打脸/反转/碾压/真相揭露",
            "冲突可视化：力量对比、身份反差、情感张力用画面展示",
            "对话简短有力：冲突对话3句话，反击1句话",
            "悬念强制：每集结尾必须卡悬念",
            "改编重构：心理→动作，叙述→画面，铺垫→删除，过程→结果",
            "信息前置：爽点前置先爽再解释"
        ],
        "structure": {
            "formula": "起承转钩",
            "word_count_per_episode": {"min": 500, "max": 800},
            "duration_seconds": {"min": 60, "max": 120},
            "scene_count": {"min": 1, "max": 3}
        },
        "constraints": {
            "dialogue_max_chars": 20,
            "dialogue_ratio": 0.35,  # 对话占30-40%
            "action_ratio": 0.45,    # 动作描写占40-50%
            "narration_ratio": 0.15  # 心理/旁白占10-20%
        },
        "visual_priority": {
            "opening": "瞬间进入画面，不要铺垫，开场就是冲突现场",
            "transformation": "快速给予金手指/觉醒/回归，从小说中提取转折点",
            "confrontation": "对比要强烈，一招制敌最爽，碾压要干脆",
            "revelation": "铺垫要隐蔽，揭露要震撼，身份反转要有料"
        }
    }


async def main():
    """主函数：执行配置导入"""
    print("=" * 60)
    print("AI 工作流配置初始化脚本")
    print("=" * 60)

    async with AsyncSessionLocal() as db:
        try:
            print("\n[1/4] 解析方法论文档...")

            # 1. 解析 adapt-method.md
            adapt_method_data = parse_adapt_method()
            print(f"  ✓ adapt-method.md 解析完成（{len(adapt_method_data)} 个配置项）")

            # 2. 解析 breakdown-aligner.md
            qa_data = parse_breakdown_aligner()
            print(f"  ✓ breakdown-aligner.md 解析完成（{len(qa_data['dimensions'])} 个质检维度）")

            # 3. 解析 output-style.md
            style_data = parse_output_style()
            print(f"  ✓ output-style.md 解析完成（{len(style_data['principles'])} 个核心原则）")

            print("\n[2/4] 准备写入数据库...")

            # 4. 创建配置记录（使用 merge 保证幂等性）
            configs = [
                AIConfiguration(
                    key="adapt_method_default",
                    category="adapt_method",
                    value=adapt_method_data,
                    description="网文改编漫剧方法论（系统默认）- 冲突提取⭐⭐⭐/⭐⭐/⭐、情绪钩子10-6分评分、压缩策略",
                    user_id=None,
                    is_active=True
                ),
                AIConfiguration(
                    key="qa_breakdown_default",
                    category="quality_rule",
                    value=qa_data,
                    description="剧情拆解质检标准（系统默认）- 8维度质量检查（冲突强度、情绪钩子、密度、分集、压缩、描述、还原、类型）",
                    user_id=None,
                    is_active=True
                ),
                AIConfiguration(
                    key="output_style_default",
                    category="prompt_template",
                    value=style_data,
                    description="漫剧输出风格（系统默认）- 起承转钩、视觉化优先、快节奏无尿点",
                    user_id=None,
                    is_active=True
                )
            ]

            print("\n[3/4] 写入配置到数据库...")

            for config in configs:
                # 检查是否已存在
                result = await db.execute(
                    select(AIConfiguration).where(
                        AIConfiguration.key == config.key,
                        AIConfiguration.user_id.is_(None)
                    )
                )
                existing = result.scalar_one_or_none()

                if existing:
                    # 更新现有配置
                    existing.value = config.value
                    existing.description = config.description
                    existing.category = config.category
                    existing.is_active = config.is_active
                    print(f"  ↻ 更新配置: {config.key} ({config.category})")
                else:
                    # 插入新配置
                    db.add(config)
                    print(f"  ✓ 新增配置: {config.key} ({config.category})")

            await db.commit()

            print("\n[4/4] 验证配置...")

            # 验证写入结果
            result = await db.execute(
                select(AIConfiguration).where(
                    AIConfiguration.user_id.is_(None),
                    AIConfiguration.category.in_(['adapt_method', 'quality_rule', 'prompt_template'])
                ).order_by(AIConfiguration.key)
            )
            all_configs = result.scalars().all()

            print(f"\n数据库中系统默认配置总数: {len(all_configs)}")
            print("\n配置列表:")
            for cfg in all_configs:
                print(f"  • {cfg.key:<30} | {cfg.category:<20} | {cfg.description[:50]}...")

            print("\n" + "=" * 60)
            print("✅ 配置初始化完成！")
            print("=" * 60)
            print("\n下一步：")
            print("  1. 验证配置：psql -d scriptflow -c \"SELECT key, category FROM ai_configurations WHERE user_id IS NULL;\"")
            print("  2. 测试 API：curl http://localhost:8000/api/v1/configurations?merge=true")
            print()

        except Exception as e:
            print(f"\n❌ 错误：{str(e)}")
            import traceback
            traceback.print_exc()
            await db.rollback()
            sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
