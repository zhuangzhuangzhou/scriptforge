import os
import importlib
from typing import Dict, List, Optional, Type
from app.ai.skills.base_skill import BaseSkill


class SkillLoader:
    """Skill加载器"""

    _instance: Optional["SkillLoader"] = None
    _initialized: bool = False

    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not SkillLoader._initialized:
            self.skills: Dict[str, BaseSkill] = {}
            self.skill_classes: Dict[str, Type[BaseSkill]] = {}
            self.load_skills()
            SkillLoader._initialized = True

    def load_skills(self, skills_dir: str = None):
        """从目录加载所有Skills"""
        if skills_dir is None:
            # 获取当前文件所在目录
            skills_dir = os.path.dirname(os.path.abspath(__file__))

        # 获取skills目录下的所有Python文件
        for filename in os.listdir(skills_dir):
            if filename.endswith("_skill.py") and filename != "base_skill.py":
                module_name = filename[:-3]  # 移除.py后缀
                self._load_skill_module(module_name)

    def _load_skill_module(self, module_name: str):
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
                    # 保存类引用
                    self.skill_classes[attr_name] = attr
                    # 实例化Skill
                    skill_instance = attr()
                    self.skills[skill_instance.name] = skill_instance
        except Exception as e:
            print(f"加载Skill {module_name} 失败: {e}")

    def get_skill(self, skill_name: str) -> Optional[BaseSkill]:
        """获取指定的Skill实例"""
        return self.skills.get(skill_name)

    def get_skill_class(self, skill_name: str) -> Optional[Type[BaseSkill]]:
        """获取指定的Skill类"""
        # 先按实例名查找
        skill = self.skills.get(skill_name)
        if skill:
            return type(skill)
        # 再按类名查找
        return self.skill_classes.get(skill_name)

    def get_all_skills(self) -> List[Dict[str, str]]:
        """获取所有Skill的元数据"""
        return [skill.get_metadata() for skill in self.skills.values()]

    def list_skill_names(self) -> List[str]:
        """获取所有Skill名称"""
        return list(self.skills.keys())

    async def execute_skill(self, skill_name: str, context: Dict) -> Dict:
        """执行指定的Skill"""
        skill = self.get_skill(skill_name)
        if not skill:
            raise ValueError(f"Skill {skill_name} 不存在")
        return await skill.execute(context)
