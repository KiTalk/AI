from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse
from services.naver_stt_service import NaverSTTService
from utils.exceptions import validate_audio_file, validate_language, handle_stt_errors
from config.settings import logger

router = APIRouter(prefix="/stt", tags=["STT"])

# STT 서비스 인스턴스 생성
try:
    stt_service = NaverSTTService()
    logger.info("STT 서비스가 성공적으로 초기화되었습니다.")
except ValueError as e:
    logger.error(f"STT 서비스 초기화 실패: {e}")
    stt_service = None

@router.post("")
async def speech_to_text(
    audio_file: UploadFile = File(...),
    lang: str = Form(default="Kor")
):
    """음성 파일을 텍스트로 변환"""
    if not stt_service:
        raise HTTPException(status_code=500, detail="STT 서비스가 초기화되지 않았습니다.")

    # 언어 유효성 검사
    validate_language(lang)

    try:
        # 파일 읽기
        audio_data = await audio_file.read()
        
        # 파일 유효성 검사
        validate_audio_file(audio_data, audio_file.filename)

        logger.info(f"음성 파일 처리 시작: {audio_file.filename}, 크기: {len(audio_data)} bytes, 언어: {lang}")

        # STT 변환
        result = stt_service.convert_speech_to_text(audio_data, lang)

        # 에러 처리
        error_response = handle_stt_errors(result)
        if error_response:
            return error_response

        if result["success"]:
            logger.info(f"STT 변환 성공: {result['text'][:50]}...")
        else:
            logger.error(f"STT 변환 실패: {result['error']}")

        return JSONResponse(content=result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"STT 처리 중 오류: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": f"서버 처리 중 오류: {str(e)}"}
        )
