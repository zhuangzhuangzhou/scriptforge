from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.skill import Skill
import uuid

# 系统内置 Skill 归属的固定 owner_id（不需要真实用户）
SYSTEM_OWNER_ID = uuid.UUID("00000000-0000-0000-0000-000000000000")


async def init_builtin_skills(db: AsyncSession):
    """初始化内置Skills到数据库"""

    builtin_skills = [
        {
            "name": "conflict_extraction",
            "display_name": "冲突点提取",
            "description": "从章节内容中提取冲突点",
            "category": "breakdown",
            "module_path": "app.ai.skills.conflict_extraction_skill",
            "class_name": "ConflictExtractionSkill",
            "owner_id": SYSTEM_OWNER_ID,
            "visibility": "public",
            "is_builtin": True,
            "is_active": True
        },
        {
            "name": "plot_hook_identification",
            "display_name": "剧情钩子识别",
            "description": "识别章节中的剧情钩子，吸引观众继续观看",
            "category": "breakdown",
            "module_path": "app.ai.skills.plot_hook_skill",
            "class_name": "PlotHookSkill",
            "owner_id": SYSTEM_OWNER_ID,
            "visibility": "public",
            "is_builtin": True,
            "is_active": True
        },
        {
            "name": "character_analysis",
            "display_name": "人物分析",
            "description": "分析章节中的人物关系、性格特点和发展轨迹",
            "category": "breakdown",
            "module_path": "app.ai.skills.character_analysis_skill",
            "class_name": "CharacterAnalysisSkill",
            "owner_id": SYSTEM_OWNER_ID,
            "visibility": "public",
            "is_builtin": True,
            "is_active": True
        },
        {
            "name": "scene_identification",
            "display_name": "场景识别",
            "description": "识别章节中的场景，包括地点、时间、氛围等",
            "category": "breakdown",
            "module_path": "app.ai.skills.scene_identification_skill",
            "class_name": "SceneIdentificationSkill",
            "owner_id": SYSTEM_OWNER_ID,
            "visibility": "public",
            "is_builtin": True,
            "is_active": True
        },
        {
            "name": "emotion_extraction",
            "display_name": "情绪点提取",
            "description": "提取章节中的情绪点，分析情感起伏",
            "category": "breakdown",
            "module_path": "app.ai.skills.emotion_extraction_skill",
            "class_name": "EmotionExtractionSkill",
            "owner_id": SYSTEM_OWNER_ID,
            "visibility": "public",
            "is_builtin": True,
            "is_active": True
        },
        {
            "name": "episode_planning",
            "display_name": "剧集规划",
            "description": "基于剧情拆解结果规划剧集结构",
            "category": "script",
            "module_path": "app.ai.skills.episode_planning_skill",
            "class_name": "EpisodePlanningSkill",
            "owner_id": SYSTEM_OWNER_ID,
            "visibility": "public",
            "is_builtin": True,
            "is_active": True
        },
        {
            "name": "scene_generation",
            "display_name": "场景生成",
            "description": "基于剧集规划和拆解结果生成场景",
            "category": "script",
            "module_path": "app.ai.skills.scene_generation_skill",
            "class_name": "SceneGenerationSkill",
            "owner_id": SYSTEM_OWNER_ID,
            "visibility": "public",
            "is_builtin": True,
            "is_active": True
        },
        {
            "name": "dialogue_writing",
            "display_name": "对话生成",
            "description": "基于场景与人物信息生成对话",
            "category": "script",
            "module_path": "app.ai.skills.dialogue_writing_skill",
            "class_name": "DialogueWritingSkill",
            "owner_id": SYSTEM_OWNER_ID,
            "visibility": "public",
            "is_builtin": True,
            "is_active": True
        },
        {
            "name": "breakdown_aligner",
            "display_name": "拆解质检",
            "description": "审核剧情拆解结果是否符合改编方法论要求",
            "category": "qa",
            "module_path": "app.ai.skills.breakdown_aligner_skill",
            "class_name": "BreakdownAlignerSkill",
            "owner_id": SYSTEM_OWNER_ID,
            "visibility": "public",
            "is_builtin": True,
            "is_active": True
        },
        {
            "name": "webtoon_aligner",
            "display_name": "剧本质检",
            "description": "检查网文改编漫剧内容的一致性和质量",
            "category": "qa",
            "module_path": "app.ai.skills.webtoon_aligner_skill",
            "class_name": "WebtoonAlignerSkill",
            "owner_id": SYSTEM_OWNER_ID,
            "visibility": "public",
            "is_builtin": True,
            "is_active": True
        }
    ]

    # 检查并插入内置Skills
    for skill_data in builtin_skills:
        # 检查是否已存在
        result = await db.execute(
            select(Skill).where(Skill.name == skill_data["name"])
        )
        existing_skill = result.scalar_one_or_none()

        if not existing_skill:
            # 创建新的Skill
            skill = Skill(**skill_data)
            db.add(skill)

    await db.commit()
    print(f"已初始化 {len(builtin_skills)} 个内置Skills")
