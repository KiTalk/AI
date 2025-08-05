from pydantic import BaseModel
from typing import Optional, List

class STTResponse(BaseModel):
    """STT 응답 모델"""
    success: bool
    text: Optional[str] = None
    confidence: Optional[float] = None
    error: Optional[str] = None
    details: Optional[str] = None
    code: Optional[str] = None

class LanguageInfo(BaseModel):
    """언어 정보 모델"""
    code: str
    name: str

class LanguagesResponse(BaseModel):
    """지원 언어 목록 응답 모델"""
    languages: List[LanguageInfo]

class HealthResponse(BaseModel):
    """헬스체크 응답 모델"""
    status: str
    service: str
    stt_service_available: bool
