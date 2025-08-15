from pydantic import BaseModel

class MenuRequest(BaseModel):
    menu_item: str  # 1단계: 메뉴 이름
