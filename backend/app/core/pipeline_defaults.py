import uuid

# 系统默认 owner_id（不需要真实用户）
SYSTEM_OWNER_ID = uuid.UUID("00000000-0000-0000-0000-000000000000")

# 默认 Pipeline 技能列表
DEFAULT_BREAKDOWN_SKILLS = [
    "conflict_extraction",
    "plot_hook_identification",
    "character_analysis",
    "scene_identification",
    "emotion_extraction",
]

DEFAULT_SCRIPT_SKILLS = [
    "episode_planning",
    "scene_generation",
    "dialogue_writing",
]

# 默认 Pipeline 阶段配置
DEFAULT_PIPELINE_STAGES = [
    {
        "name": "breakdown",
        "display_name": "剧情拆解",
        "description": "剧情拆解阶段（默认配置）",
        "order": 0,
        "skills": DEFAULT_BREAKDOWN_SKILLS,
        "config": {
            "validators": [
                {"type": "consistency_checker"}
            ]
        }
    },
    {
        "name": "script",
        "display_name": "剧本生成",
        "description": "剧本生成阶段（默认配置）",
        "order": 1,
        "skills": DEFAULT_SCRIPT_SKILLS,
        "config": {}
    }
]
