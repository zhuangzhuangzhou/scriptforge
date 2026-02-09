"""计费规则 Schema 定义"""
from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime
from decimal import Decimal


class PricingBase(BaseModel):
    """计费规则基础Schema"""
    input_credits_per_1k_tokens: Decimal = Field(..., description="输入 Token 价格（每 1000 tokens）")
    output_credits_per_1k_tokens: Decimal = Field(..., description="输出 Token 价格（每 1000 tokens）")
    min_credits_per_request: Decimal = Field(Decimal('0'), description="每次请求最低积分")
    effective_from: Optional[datetime] = Field(None, description="生效时间")
    effective_until: Optional[datetime] = Field(None, description="失效时间")


class PricingCreate(PricingBase):
    """创建计费规则请求"""
    model_id: str = Field(..., description="模型ID")


class PricingUpdate(BaseModel):
    """更新计费规则请求"""
    input_credits_per_1k_tokens: Optional[Decimal] = None
    output_credits_per_1k_tokens: Optional[Decimal] = None
    min_credits_per_request: Optional[Decimal] = None
    effective_from: Optional[datetime] = None
    effective_until: Optional[datetime] = None
    is_active: Optional[bool] = None


class ModelInfo(BaseModel):
    """模型信息（嵌套对象）"""
    id: str
    model_key: str
    display_name: str

    class Config:
        from_attributes = True


class PricingResponse(PricingBase):
    """计费规则响应"""
    id: str
    model: ModelInfo = Field(..., description="模型信息")
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
