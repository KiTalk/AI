from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field

class MenuMatch(BaseModel):
    """메뉴 매칭 결과"""
    name: str = Field(..., description="매칭된 메뉴명")
    category: Optional[str] = Field(None, description="메뉴 카테고리")
    similarity: float = Field(..., ge=0.0, le=1.0, description="유사도 점수")

class MenuInfo(BaseModel):
    """메뉴 정보"""
    name: str = Field(..., description="선택된 메뉴명")
    similarity: float = Field(..., ge=0.0, le=1.0, description="유사도 점수")
    candidates: List[MenuMatch] = Field(default=[], description="유사 메뉴 후보들")
    method: str = Field(..., description="매칭 방법 (vector_search, keyword_match, etc.)")
    error: Optional[str] = Field(None, description="오류 메시지")

class PackagingInfo(BaseModel):
    """포장 정보"""
    type: str = Field(..., description="포장 타입 (포장/매장식사)")
    similarity: float = Field(..., ge=0.0, le=1.0, description="유사도 점수")
    method: str = Field(..., description="매칭 방법")

class OrderInfo(BaseModel):
    """주문 정보"""
    menu: MenuInfo = Field(..., description="메뉴 정보")
    quantity: int = Field(..., ge=1, description="수량")
    packaging: PackagingInfo = Field(..., description="포장 정보")
    original_text: str = Field(..., description="원본 음성 인식 텍스트")
    error: Optional[str] = Field(None, description="처리 중 오류")

class OrderAtOnceResponse(BaseModel):
    """한번에 주문 응답"""
    success: bool = Field(..., description="처리 성공 여부")
    recognized_text: str = Field(..., description="음성 인식된 텍스트")
    confidence: float = Field(..., ge=0.0, le=1.0, description="음성 인식 신뢰도")
    order_info: OrderInfo = Field(..., description="추출된 주문 정보")
    error: Optional[str] = Field(None, description="오류 메시지")

class MenuSimilarityResponse(BaseModel):
    """메뉴 유사도 검색 응답"""
    success: bool = Field(..., description="검색 성공 여부")
    query: str = Field(..., description="검색 쿼리")
    similar_menus: List[MenuMatch] = Field(..., description="유사한 메뉴 목록")
    error: Optional[str] = Field(None, description="오류 메시지")

# 벡터 DB 관련 모델
class VectorMenuItem(BaseModel):
    """벡터 DB용 메뉴 아이템"""
    id: str = Field(..., description="메뉴 고유 ID")
    name: str = Field(..., description="메뉴명")
    category: str = Field(..., description="카테고리")
    price: Optional[int] = Field(None, description="가격")
    description: Optional[str] = Field(None, description="메뉴 설명")
    keywords: List[str] = Field(default=[], description="검색 키워드")
    is_available: bool = Field(default=True, description="판매 가능 여부")

class VectorPackagingOption(BaseModel):
    """벡터 DB용 포장 옵션"""
    id: str = Field(..., description="옵션 고유 ID")
    type: str = Field(..., description="포장 타입")
    keywords: List[str] = Field(..., description="관련 키워드")
    description: Optional[str] = Field(None, description="설명")
