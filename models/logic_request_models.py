from pydantic import BaseModel, Field

# 주문 시작 요청
class StartOrderRequest(BaseModel):
    pass

# 메뉴 선택 요청
class MenuRequest(BaseModel):
    menu_item: str = Field(..., description="메뉴 이름")

    class Config:
        schema_extra = {
            "example": {
                "menu_item": "라면"
            }
        }

class PackagingRequest(BaseModel):
    packaging_type: str = Field(..., description="포장 방식")

    class Config:
        schema_extra = {
            "example": {
                "packaging_type": "포장"
            }
        }