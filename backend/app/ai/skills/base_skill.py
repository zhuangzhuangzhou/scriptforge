from abc import ABC, abstractmethod
from typing import Dict, Any


class BaseSkill(ABC):
    """Skill基类"""

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    @abstractmethod
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """执行Skill"""
        pass

    def get_metadata(self) -> Dict[str, Any]:
        """获取Skill元数据"""
        return {
            "name": self.name,
            "description": self.description
        }
