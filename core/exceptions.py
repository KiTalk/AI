from fastapi import HTTPException
from fastapi.responses import JSONResponse
from config.naver_stt_settings import logger

class STTException(Exception):
    """STT 관련 커스텀 예외"""
    def __init__(self, message: str, code: str = None):
        self.message = message
        self.code = code
        super().__init__(self.message)

def handle_stt_errors(result: dict) -> JSONResponse:
    """STT 결과에 따른 에러 처리"""
    if result["success"]:
        return None
    
    # 네이버 STT 특정 오류 처리
    details = str(result.get("details", ""))
    
    if "STT007" in details:
        return JSONResponse(content={
            "success": False, 
            "error": "음성이 너무 짧거나 인식할 수 없습니다. 더 길게 말씀해주세요.",
            "code": "AUDIO_TOO_SHORT"
        })
    elif "STT006" in details:
        return JSONResponse(content={
            "success": False, 
            "error": "지원하지 않는 오디오 형식입니다.",
            "code": "UNSUPPORTED_FORMAT"
        })
    
    return JSONResponse(content=result)

def validate_audio_file(audio_data: bytes, filename: str = None) -> None:
    """오디오 파일 유효성 검사"""
    from config.naver_stt_settings import settings
    
    if len(audio_data) == 0:
        raise HTTPException(status_code=400, detail="비어있는 오디오 파일입니다.")
    
    if len(audio_data) > settings.MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="파일 크기가 너무 큽니다. (최대 50MB)")
    
    if len(audio_data) < settings.MIN_FILE_SIZE:
        raise HTTPException(
            status_code=400, 
            detail="음성이 너무 짧습니다. 최소 1초 이상 녹음해주세요."
        )

def validate_language(lang: str) -> None:
    """언어 유효성 검사"""
    from config.naver_stt_settings import settings
    
    if lang not in settings.SUPPORTED_LANGUAGES:
        raise HTTPException(
            status_code=400, 
            detail=f"지원되지 않는 언어입니다. 지원 언어: {settings.SUPPORTED_LANGUAGES}"
        )
