from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, Field, validator
from enum import Enum

class TempType(str, Enum):
    hot = "hot"
    ice = "ice"
    none = "none"

class PackagingType(str, Enum):
    TAKEOUT = "포장"
    DINEIN = "매장식사"

class OrderAtOnceTextRequest(BaseModel):
    text: str = Field(..., description="주문 텍스트")

class VectorMenuItem(BaseModel):
    menu_id: int = Field(..., description="메뉴 고유 ID")
    name: str = Field(..., description="메뉴명")
    category: Optional[str] = Field(None, description="카테고리")
    price: int = Field(..., description="가격")
    popular: bool = Field(default=False, description="인기 메뉴 여부")
    temp: TempType = Field(TempType.none, description="온도 (hot/ice/none)")
    description: Optional[str] = Field(None, description="메뉴 설명")
    keywords: List[str] = Field(default_factory=list, description="검색 키워드")
    is_available: bool = Field(default=True, description="판매 가능 여부")

class VectorPackagingOption(BaseModel):
    id: int = Field(..., description="옵션 고유 ID (정수)")
    type: PackagingType = Field(..., description="포장 타입 ('포장' 또는 '매장식사')")
    keywords: List[str] = Field(default_factory=list, description="관련 키워드")
    description: Optional[str] = Field(None, description="설명")

    @validator("keywords")
    def _trim_keywords(cls, v: List[str]) -> List[str]:
        return [s.strip() for s in v if isinstance(s, str)]
