"""AI 模型 Schema 定义"""
from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime
from decimal import Decimal


class AIModelBase(BaseModel):
    """AI模型基础Schema"""
    model_key: str = Field(..., description="模型标识", max_length=100)
    display_name: str = Field(..., description="显示名称", max_length=100)
    model_type: Optional[str] = Field(None, description="模型类型", max_length=50)
    max_tokens: Optional[int] = Field(None, description="最大Token数")
    max_input_tokens: Optional[int] = Field(None, description="最大输入Token数")
    max_output_tokens: Optional[int] = Field(None, description="最大输出Token数")
    timeout_seconds: int = Field(120, description="超时时间（秒）")
    temperature_default: Decimal = Field(Decimal('0.7'), description="默认温度")
    supports_streaming: bool = Field(True, description="支持流式输出")
    supports_function_calling: bool = Field(False, description="支持函数调用")
    description: Optional[str] = Field(None, description="描述")


class AIModelCreate(AIModelBase):
    """创建模型请求"""
    provider_id: str = Field(..., description="提供商ID")


class AIModelUpdate(BaseModel):
    """更新模型请求"""
    display_name: Optional[str] = Field(None, max_length=100)
    model_type: Optional[str] = Field(None, max_length=50)
    is_enabled: Optional[bool] = None
    max_tokens: Optional[int] = None
    max_input_tokens: Optional[int] = None
    max_output_tokens: Optional[int] = None
    timeout_seconds: Optional[int] = None
    temperature_default: Optional[Decimal] = None
    supports_streaming: Optional[bool] = None
    supports_function_calling: Optional[bool] = None
    description: Optional[str] = None


class AIModelResponse(AIModelBase):
    """模型响应"""
    id: str
    provider_id: str
    provider_name: str = Field(..., description="提供商名称")
    is_enabled: bool
    is_default: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
