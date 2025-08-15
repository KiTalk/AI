from pydantic import BaseModel, Field
from typing import Union

class MenuRequest(BaseModel):
    menu_item: str  # 1단계: 메뉴 이름

class QuantityRequest(BaseModel):
    quantity: Union[int, str] = Field(..., description="수량 (숫자 또는 자연어)")

    class Config:
        schema_extra = {
            "example": {
                "quantity": "2잔"
            }
        }