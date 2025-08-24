from pydantic import BaseModel
from typing import List, Optional, Dict, Any, Union

class OrderItem(BaseModel):
    menu_id: int
    menu_item: str
    price: int
    quantity: int
    original: str
    popular: bool = False
    temp: str = "hot"
    profile: Optional[Union[str, Dict[str, Any]]] = None

class StandardResponse(BaseModel):
    message: str
    orders: List[OrderItem] = []
    total_items: int = 0
    total_price: int = 0
    packaging:Optional[str] = None
    session_id: str
    next_step: Optional[str] = None

class ErrorResponse(BaseModel):
    message: str
    session_id: str
    next_step: str
    retry: bool = True

class SessionResponse(StandardResponse):
    pass