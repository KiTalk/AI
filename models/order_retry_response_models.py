from typing import Any, Dict, Optional
from pydantic import BaseModel

class MenuRetryResponse(BaseModel):
    session_id: str
    message: str
    menu: Dict[str, Any]

class PackagingRetryResponse(BaseModel):
    session_id: str
    message: str
    packaging: str

class TempRetryResponse(BaseModel):
    session_id: str
    message: str
    temp: str
    menu_id: Optional[int] = None