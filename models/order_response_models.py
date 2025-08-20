from __future__ import annotations
from typing import List, Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field

# 팀원이 작업한 단계별 주문 모델들 (유지)
class PackagingType(str, Enum):
    TAKEOUT = "포장"
    DINEIN = "매장식사"

class OrderItem(BaseModel):
    menu_item: str
    price: int = 0
    quantity: int = 1
    original: str

class StandardResponse(BaseModel):
    message: str
    orders: List[OrderItem] = Field(default_factory=list)
    total_items: int = 0
    total_price: int = 0
    packaging: Optional[PackagingType] = None
    session_id: str
    missing: List[str] = Field(default_factory=list)  # 누락된 슬롯
    debug: Optional[Dict[str, Any]] = None

class ErrorResponse(BaseModel):
    message: str
    session_id: str
    retry: bool = True
    debug: Optional[Dict[str, Any]] = None

class SessionResponse(StandardResponse):
    pass

# 한번에 주문하기(order_at_once) 전용 응답 모델들

class MenuMatch(BaseModel):
    """메뉴 매칭 결과"""
    name: str = Field(..., description="매칭된 메뉴명")
    category: Optional[str] = Field(None, description="메뉴 카테고리")
    similarity: float = Field(..., ge=0.0, le=1.0, description="유사도 점수")
    popular: Optional[bool] = Field(None, description="인기 메뉴 여부")
    temp: Optional[str] = Field(None, description="온도 옵션 (ice/hot)")
    price: Optional[int] = Field(None, description="가격")

class SingleMenuInfo(BaseModel):
    """단일 메뉴 정보 (한번에 주문용)"""
    name: str = Field(..., description="선택된 메뉴명")
    quantity: int = Field(..., ge=1, description="수량")
    similarity: float = Field(..., ge=0.0, le=1.0, description="유사도 점수")
    popular: Optional[bool] = Field(None, description="인기 메뉴 여부")
    temp: Optional[str] = Field(None, description="온도 옵션 (ice/hot)")
    price: Optional[int] = Field(None, description="가격")
    candidates: List[MenuMatch] = Field(default=[], description="유사 메뉴 후보들")
    method: str = Field(..., description="매칭 방법 (fuzzywuzzy, vector_search, etc.)")
    error: Optional[str] = Field(None, description="오류 메시지")

class OrderAtOnceInfo(BaseModel):
    """한번에 주문 정보"""
    menu: SingleMenuInfo = Field(..., description="메뉴 정보")
    original_text: str = Field(..., description="원본 음성 인식 텍스트")
    session_id: str = Field(..., description="Redis 세션 ID")
    error: Optional[str] = Field(None, description="처리 중 오류")

class SimpleOrderAtOnce(BaseModel):
    """프론트엔드용 간단한 주문 정보 (단일)"""
    menu_item: str = Field(..., description="메뉴명")
    price: int = Field(default=0, description="가격")
    quantity: int = Field(..., description="수량")
    popular: Optional[bool] = Field(None, description="인기 메뉴 여부")
    temp: Optional[str] = Field(None, description="온도 옵션")
    session_id: str = Field(..., description="세션 ID")

class OrderAtOnceResponse(BaseModel):
    """한번에 주문 응답 (음성 파일 처리)"""
    success: bool = Field(..., description="처리 성공 여부")
    recognized_text: str = Field(..., description="음성 인식된 텍스트")
    confidence: float = Field(..., ge=0.0, le=1.0, description="음성 인식 신뢰도")
    order_info: OrderAtOnceInfo = Field(..., description="추출된 주문 정보")
    simple: SimpleOrderAtOnce = Field(..., description="프론트엔드용 간단한 형태")
    error: Optional[str] = Field(None, description="오류 메시지")

class TextOrderResponse(BaseModel):
    """텍스트 주문 응답"""
    success: bool = Field(..., description="처리 성공 여부")
    recognized_text: str = Field(..., description="입력된 텍스트")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="신뢰도 (텍스트는 1.0)")
    order_info: OrderAtOnceInfo = Field(..., description="추출된 주문 정보")
    simple: SimpleOrderAtOnce = Field(..., description="프론트엔드용 간단한 형태")
    error: Optional[str] = Field(None, description="오류 메시지")

class MenuSimilarityResponse(BaseModel):
    """메뉴 유사도 검색 응답"""
    success: bool = Field(default=True, description="검색 성공 여부")
    query: str = Field(..., description="검색 쿼리")
    results: List[MenuMatch] = Field(..., description="유사한 메뉴 목록")
    error: Optional[str] = Field(None, description="오류 메시지")

class SessionOrderResponse(BaseModel):
    """세션 주문 조회 응답"""
    success: bool = Field(..., description="조회 성공 여부")
    session_id: str = Field(..., description="세션 ID")
    order_data: Optional[Dict[str, Any]] = Field(None, description="주문 데이터")
    error: Optional[str] = Field(None, description="오류 메시지")
