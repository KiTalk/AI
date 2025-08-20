from typing import List, Optional
from pydantic import BaseModel, Field

# 한번에 주문하기 요청 모델들

class OrderAtOnceTextRequest(BaseModel):
    """텍스트 기반 한번에 주문 요청"""
    text: str = Field(..., description="주문 텍스트")

class MenuSimilarityRequest(BaseModel):
    """메뉴 유사도 검색 요청"""
    name: str = Field(..., description="검색할 메뉴명")
    limit: int = Field(default=5, ge=1, le=20, description="검색 결과 제한")

# 벡터 DB 초기화용 모델들

class VectorMenuItem(BaseModel):
    """벡터 DB용 메뉴 아이템"""
    id: str = Field(..., description="메뉴 고유 ID")
    name: str = Field(..., description="메뉴명")
    category: str = Field(..., description="카테고리")
    price: Optional[int] = Field(None, description="가격")
    popular: Optional[bool] = Field(None, description="인기 메뉴 여부")
    temp: Optional[str] = Field(None, description="기본 온도 (ice/hot)")
    description: Optional[str] = Field(None, description="메뉴 설명")
    keywords: List[str] = Field(default=[], description="검색 키워드")
    is_available: bool = Field(default=True, description="판매 가능 여부")

class VectorPackagingOption(BaseModel):
    """벡터 DB용 포장 옵션"""
    id: str = Field(..., description="옵션 고유 ID")
    type: str = Field(..., description="포장 타입")
    keywords: List[str] = Field(..., description="관련 키워드")
    description: Optional[str] = Field(None, description="설명")
