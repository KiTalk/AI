from pydantic import BaseModel
from typing import Optional, List

class STTResponse(BaseModel):
    success: bool
    text: Optional[str] = None
    confidence: Optional[float] = None
    error: Optional[str] = None
    details: Optional[str] = None
    code: Optional[str] = None

class LanguageInfo(BaseModel):
    code: str
    name: str

class LanguagesResponse(BaseModel):
    languages: List[LanguageInfo]

class HealthResponse(BaseModel):
    status: str
    service: str
    stt_service_available: bool
