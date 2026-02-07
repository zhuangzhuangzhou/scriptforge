from pydantic import BaseModel, Field
from typing import Any, Optional
from datetime import datetime
from uuid import UUID

class AIConfigurationBase(BaseModel):
    key: str = Field(..., description="配置键名")
    value: Any = Field(..., description="配置内容 (JSON)")
    description: Optional[str] = Field(None, description="配置描述")

class AIConfigurationCreate(AIConfigurationBase):
    pass

class AIConfigurationUpdate(BaseModel):
    value: Optional[Any] = None
    description: Optional[str] = None

class AIConfiguration(AIConfigurationBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
