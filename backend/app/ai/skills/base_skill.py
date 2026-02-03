from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class BaseSkill(ABC):
    """Skill基类"""

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.parameters: Dict[str, Any] = {}

    @abstractmethod
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """执行Skill"""
        pass

    def set_parameters(self, parameters: Dict[str, Any]) -> None:
        """设置执行参数"""
        self.parameters.update(parameters)

    def get_parameter(self, key: str, default: Any = None) -> Any:
        """获取单个参数"""
        return self.parameters.get(key, default)

    def get_metadata(self) -> Dict[str, Any]:
        """获取Skill元数据"""
        return {
            "name": self.name,
            "description": self.description
        }
