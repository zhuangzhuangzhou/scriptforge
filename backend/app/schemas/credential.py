"""凭证管理 Schema 定义"""
from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime


class CredentialBase(BaseModel):
    """凭证基础Schema"""
    credential_name: str = Field(..., description="凭证名称", max_length=100)
    quota_limit: Optional[int] = Field(None, description="配额限制")
    expires_at: Optional[datetime] = Field(None, description="过期时间")


class CredentialCreate(CredentialBase):
    """创建凭证请求"""
    provider_id: str = Field(..., description="提供商ID")
    api_key: str = Field(..., description="API Key（明文）")
    api_secret: Optional[str] = Field(None, description="API Secret（明文，可选）")


class CredentialUpdate(BaseModel):
    """更新凭证请求"""
    credential_name: Optional[str] = Field(None, max_length=100)
    api_key: Optional[str] = Field(None, description="新的 API Key（明文）")
    api_secret: Optional[str] = Field(None, description="新的 API Secret（明文）")
    is_active: Optional[bool] = None
    quota_limit: Optional[int] = None
    expires_at: Optional[datetime] = None


class ProviderInfo(BaseModel):
    """提供商信息（嵌套对象）"""
    id: str
    provider_key: str
    display_name: str

    class Config:
        from_attributes = True


class CredentialResponse(CredentialBase):
    """凭证响应（API Key 脱敏）"""
    id: str
    provider: ProviderInfo = Field(..., description="提供商信息")
    api_key_masked: str = Field(..., description="脱敏后的 API Key")
    is_active: bool
    is_system_default: bool
    quota_used: int = Field(0, description="已使用配额")
    quota_remaining: Optional[int] = Field(None, description="剩余配额")
    last_used_at: Optional[datetime] = Field(None, description="最后使用时间")
    created_by: Optional[str] = Field(None, description="创建者ID")
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
