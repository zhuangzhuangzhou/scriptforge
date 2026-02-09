"""系统配置 Schema 定义"""
from typing import Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime


class SystemConfigBase(BaseModel):
    """系统配置基础Schema"""
    config_key: str = Field(..., description="配置键", max_length=100)
    config_value: dict = Field(..., description="配置值（JSON 格式）")
    value_type: str = Field(..., description="值类型", max_length=50)
    description: Optional[str] = Field(None, description="配置说明")
    is_editable: bool = Field(True, description="是否可编辑")


class SystemConfigUpdate(BaseModel):
    """更新系统配置请求"""
    config_value: dict = Field(..., description="新的配置值")


class SystemConfigResponse(SystemConfigBase):
    """系统配置响应"""
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
