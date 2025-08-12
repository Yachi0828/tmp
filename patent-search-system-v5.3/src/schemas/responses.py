# src/schemas/responses.py
from pydantic import BaseModel
from typing import Generic, TypeVar, Optional, Any
from datetime import datetime

T = TypeVar('T')

class APIResponse(BaseModel, Generic[T]):
    """標準API響應格式"""
    success: bool = True
    data: Optional[T] = None
    message: str = ""
    timestamp: datetime = datetime.utcnow()
    request_id: Optional[str] = None

class PaginatedResponse(BaseModel, Generic[T]):
    """分頁響應格式"""
    items: List[T]
    total: int
    page: int
    size: int
    pages: int

class ErrorResponse(BaseModel):
    """錯誤響應格式"""
    success: bool = False
    error_code: str
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = datetime.utcnow()