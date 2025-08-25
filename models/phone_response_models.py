from pydantic import BaseModel, Field
from typing import List, Optional
from .logic_response_models import OrderItem

class PhoneChoiceResponse(BaseModel):
    message: str = Field(..., description="응답 메시지")
    session_id: str = Field(..., description="세션 ID")
    next_step: str = Field(..., description="다음 단계")

    class Config:
        json_schema_extra = {
            "example": {
                "message": "전화번호를 입력해주세요.",
                "session_id": "abc123",
                "next_step": "전화번호 입력"
            }
        }

class OrderCompleteResponse(BaseModel):
    message: str = Field(..., description="완료 메시지")
    order_id: int = Field(..., description="생성된 주문 ID")
    orders: List[OrderItem] = Field(..., description="주문 목록")
    total_items: int = Field(..., description="총 아이템 수")
    total_price: int = Field(..., description="총 가격")
    packaging: str = Field(..., description="포장 방식")
    phone_number: Optional[str] = Field(None, description="전화번호")
    session_id: str = Field(..., description="세션 ID")
    next_step: str = Field(..., description="다음 단계")

    class Config:
        json_schema_extra = {
            "example": {
                "message": "주문이 완료되었습니다!",
                "order_id": 123,
                "orders": [],
                "total_items": 3,
                "total_price": 15000,
                "packaging": "매장",
                "phone_number": "010-1234-5678",
                "session_id": "abc123",
                "next_step": "주문 완료"
            }
        }