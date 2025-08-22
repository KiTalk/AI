from pydantic import BaseModel
from typing import List, Optional, Literal
from datetime import datetime

AllowedStatus = Literal["PAID", "COMPLETED"]

class OrderItemOut(BaseModel):
    menu_id: Optional[int] = None
    menu_name: str
    price: int
    quantity: int
    temp: Optional[str] = None

class OrderOut(BaseModel):
    id: int
    phone_number: Optional[str] = None
    total_price: int
    packaging_type: Optional[str] = None
    created_at: datetime
    status: AllowedStatus
    items: List[OrderItemOut]

class OrderStatusUpdateRes(BaseModel):
    id: int
    status: AllowedStatus
