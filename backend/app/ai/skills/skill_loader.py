import os
import importlib
from typing import Dict, List
from app.ai.skills.base_skill import BaseSkill


class SkillLoader:
    """Skill加载器"""

    def __init__(self):
        self.skills: Dict[str, BaseSkill] = {}

    def load_skills(self, skills_dir: str = "app/ai/skills"):
        """从目录加载所有Skills"""
        # 获取skills目录下的所有Python文件
        for filename in os.listdir(skills_dir):
            if filename.endswith("_skill.py") and filename != "base_skill.py":
                module_name = filename[:-3]  # 移除.py后缀
                self._load_skill_module(module_name, skills_dir)

    def _load_skill_module(self, module_name: str, skills_dir: str):
        """加载单个Skill模块"""
        try:
            # 动态导入模块
            module_path = f"app.ai.skills.{module_name}"
            module = importlib.import_module(module_path)

            # 查找继承自BaseSkill的类
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type) and
                    issubclass(attr, BaseSkill) and
                    attr != BaseSkill):
                    # 实例化Skill
                    skill_instance = attr()
                    self.skills[skill_instance.name] = skill_instance
        except Exception as e:
            print(f"加载Skill {module_name} 失败: {e}")

    def get_skill(self, skill_name: str) -> BaseSkill:
        """获取指定的Skill"""
        return self.skills.get(skill_name)

    def get_all_skills(self) -> List[Dict[str, str]]:
        """获取所有Skill的元数据"""
        return [skill.get_metadata() for skill in self.skills.values()]

    async def execute_skill(self, skill_name: str, context: Dict) -> Dict:
        """执行指定的Skill"""
        skill = self.get_skill(skill_name)
        if not skill:
            raise ValueError(f"Skill {skill_name} 不存在")
        return await skill.execute(context)
