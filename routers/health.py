from fastapi import APIRouter
from models.stt_models import HealthResponse, LanguagesResponse, LanguageInfo
from config.naver_stt_settings import settings

router = APIRouter(tags=["Health"])

@router.get("/health", response_model=HealthResponse)
async def health_check():
    # STT 서비스 사용 가능 여부 확인
    try:
        from services.naver_stt_service import NaverSTTService
        stt_available = True
        try:
            NaverSTTService()
        except:
            stt_available = False
    except:
        stt_available = False
    
    return HealthResponse(
        status="healthy",
        service="Naver STT API",
        stt_service_available=stt_available
    )

@router.get("/languages", response_model=LanguagesResponse)
async def get_supported_languages():
    language_map = {
        "Kor": "한국어",
        "Eng": "영어", 
        "Jpn": "일본어",
        "Chn": "중국어(간체)"
    }
    
    languages = [
        LanguageInfo(code=code, name=language_map[code])
        for code in settings.SUPPORTED_LANGUAGES
        if code in language_map
    ]
    
    return LanguagesResponse(languages=languages)
