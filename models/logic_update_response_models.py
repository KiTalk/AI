from pydantic import BaseModel, Field
from typing import List

# Request용 간단한 주문 아이템 모델
class SimpleOrderItem(BaseModel):
    menu_item: str = Field(..., description="메뉴명")
    quantity: int = Field(..., gt=0, description="수량 (1개 이상)")
    temp: str = Field(..., description="온도 (ice/hot)")

    class Config:
        json_schema_extra = {
            "example": {
                "menu_item": "아메리카노",
                "quantity": 3,
                "temp": "ice"
            }
        }

# 전체 주문 업데이트 요청 모델
class UpdateAllOrdersRequest(BaseModel):
    orders: List[SimpleOrderItem] = Field(..., description="전체 주문 목록")

    class Config:
        json_schema_extra = {
            "example": {
                "orders": [
                    {"menu_item": "아메리카노", "quantity": 2, "temp": "ice"},
                    {"menu_item": "아메리카노", "quantity": 1, "temp": "hot"},
                    {"menu_item": "말차 프라페", "quantity": 1, "temp": "ice"}
                ]
            }
        }

# 추가 주문
class AddOrderRequest(BaseModel):
    order_text: str = Field(..., description="추가할 주문 텍스트")

    class Config:
        json_schema_extra = {
            "example": {
                "order_text": "플레인 스콘 1개"
            }
        }

# 주문 삭제
class RemoveOrderRequest(BaseModel):
    menu_item: str = Field(..., description="삭제할 메뉴명")
    temp: str = Field(..., description="ice/hot")

    class Config:
        json_schema_extra = {
            "example": {
                "menu_item": "아메리카노",
                "temp": "hot"
            }
        }


# Response Model
class OrderManagementResponse(BaseModel):
    success: bool = Field(..., description="요청 성공 여부")
    message: str = Field(..., description="응답 메시지")
    orders: list = Field(..., description="현재 주문 목록")
    total_items: int = Field(..., description="총 주문 아이템 수")
    total_price: int = Field(..., description="총 주문 가격")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "'라면' 수량이 5개로 변경되었습니다.",
                "orders": [
                    {
                        "menu_id": 1,
                        "menu_item": "라면",
                        "price": 3500,
                        "quantity": 5,
                        "original": "라면 3그릇"
                    }
                ],
                "total_items": 5,
                "total_price": 17500
            }
        }