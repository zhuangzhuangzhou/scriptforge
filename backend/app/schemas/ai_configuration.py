from pydantic import BaseModel, Field
from typing import Any, Optional
from datetime import datetime
from uuid import UUID

class AIConfigurationBase(BaseModel):
    key: str = Field(..., description="配置键名")
    value: Any = Field(..., description="配置内容 (JSON)")
    category: Optional[str] = Field(None, description="分类 (adapt_method, prompt_template, quality_rule)")
    is_active: bool = Field(True, description="是否激活")
    description: Optional[str] = Field(None, description="配置描述")

class AIConfigurationCreate(AIConfigurationBase):
    pass

class AIConfigurationUpdate(BaseModel):
    value: Optional[Any] = None
    category: Optional[str] = None
    is_active: Optional[bool] = None
    description: Optional[str] = None

class AIConfiguration(AIConfigurationBase):
    id: UUID
    user_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
