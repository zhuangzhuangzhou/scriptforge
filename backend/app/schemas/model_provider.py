"""模型提供商 Schema 定义"""
from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime


class ProviderBase(BaseModel):
    """提供商基础Schema"""
    provider_key: str = Field(..., description="提供商唯一标识", max_length=50)
    display_name: str = Field(..., description="显示名称", max_length=100)
    provider_type: str = Field(..., description="提供商类型", max_length=50)
    api_endpoint: Optional[str] = Field(None, description="API 端点 URL")
    icon_url: Optional[str] = Field(None, description="图标 URL")
    description: Optional[str] = Field(None, description="描述")


class ProviderCreate(ProviderBase):
    """创建提供商请求"""
    pass


class ProviderUpdate(BaseModel):
    """更新提供商请求"""
    display_name: Optional[str] = Field(None, max_length=100)
    provider_type: Optional[str] = Field(None, max_length=50, description="提供商类型")
    api_endpoint: Optional[str] = None
    is_enabled: Optional[bool] = None
    icon_url: Optional[str] = None
    description: Optional[str] = None


class ProviderResponse(ProviderBase):
    """提供商响应"""
    id: str
    is_enabled: bool
    is_system_default: bool
    models_count: int = Field(0, description="关联的模型数量")
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
