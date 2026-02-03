# 在app/main.py中添加
from app.ai.skills.skill_loader import SkillLoader

# 创建全局Skill加载器
skill_loader = SkillLoader()

@app.on_event("startup")
async def startup_event():
    """应用启动时加载Skills"""
    skill_loader.load_skills()
    print(f"已加载 {len(skill_loader.skills)} 个Skills")
