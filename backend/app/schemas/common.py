"""通用响应模型"""
from typing import Generic, TypeVar, Optional, List
from pydantic import BaseModel

T = TypeVar('T')


class SuccessResponse(BaseModel):
    """成功响应"""
    success: bool = True
    message: str
    data: Optional[dict] = None


class PaginationParams(BaseModel):
    """分页参数"""
    page: int = 1
    page_size: int = 20
    sort_by: Optional[str] = "created_at"
    sort_order: Optional[str] = "desc"
    search: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "page": 1,
                "page_size": 20,
                "sort_by": "created_at",
                "sort_order": "desc",
                "search": "openai"
            }
        }


class PaginatedResponse(BaseModel, Generic[T]):
    """分页响应"""
    items: List[T]
    total: int
    page: int
    page_size: int
    total_pages: int

    class Config:
        json_schema_extra = {
            "example": {
                "items": [],
                "total": 100,
                "page": 1,
                "page_size": 20,
                "total_pages": 5
            }
        }


class BatchOperationRequest(BaseModel):
    """批量操作请求"""
    ids: List[str]

    class Config:
        json_schema_extra = {
            "example": {
                "ids": ["uuid1", "uuid2", "uuid3"]
            }
        }


class BatchOperationResponse(BaseModel):
    """批量操作响应"""
    success_count: int
    failed_count: int
    failed_ids: List[str] = []
    message: str

    class Config:
        json_schema_extra = {
            "example": {
                "success_count": 2,
                "failed_count": 1,
                "failed_ids": ["uuid3"],
                "message": "批量操作完成：成功 2 个，失败 1 个"
            }
        }
