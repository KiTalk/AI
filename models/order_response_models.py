from __future__ import annotations
from typing import Optional
from enum import Enum
from pydantic import BaseModel, Field

class PackagingType(str, Enum):
    TAKEOUT = "포장"
    DINEIN = "매장식사"

class OrderItem(BaseModel):
    menu_id: Optional[int] = Field(None, description="Qdrant 상 메뉴 ID (온도별로 다를 수 있음)")
    menu_item: str = Field(..., description="메뉴명")
    price: int = Field(..., description="단가")
    quantity: int = Field(..., ge=1, description="수량")
    original: str = Field(..., description="원본 텍스트")
    popular: Optional[bool] = Field(None, description="인기 메뉴 여부")
    temp: Optional[str] = Field(None, description="온도 옵션 (hot/ice/none)")

class StandardResponse(BaseModel):
    message: str
    order: Optional[OrderItem] = None
    total_items: Optional[int] = None
    total_price: Optional[int] = None
    packaging: Optional[PackagingType] = None
    session_id: str
    next_step: Optional[str] = None

class ErrorResponse(BaseModel):
    message: str
    session_id: str
    retry: bool = True
