from pydantic import BaseModel, Field, HttpUrl, constr
from typing import Optional, Literal

Temperature = Literal['hot', 'ice', 'none']
Category = Literal['커피','스무디','버블티','주스','디저트','기타 음료','스페셜 티','에이드','차','프라페','특색 라떼']

class OwnerMenuCreateRequest(BaseModel):
    name: constr(strip_whitespace=True, min_length=1, max_length=120)
    temperature: Temperature
    price: int = Field(..., ge=0)
    category: Category
    popular: bool = False
    profile: Optional[HttpUrl] = None

class OwnerMenuCreateResponse(BaseModel):
    id: int
    name: str
    temperature: Temperature
    price: int
    category: Category
    popular: bool
    profile: Optional[str] = None
