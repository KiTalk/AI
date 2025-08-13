from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional

from services.order_at_once_service import OrderAtOnceService
from config.naver_stt_settings import logger
from core.exceptions import validate_language

router = APIRouter(prefix="/order-at-once", tags=["Order At Once"])

# ===== 요청/응답 모델 =====
class ProcessTextRequest(BaseModel):
    text: str = Field(..., description="이미 STT가 끝난 주문 문장")
    lang: Optional[str] = Field("Kor", description="언어 코드 (기본: Kor)")

class ProcessFlatResponse(BaseModel):
    success: bool
    menu: str
    quantity: int
    packaging: str

# ===== 서비스 인스턴스 =====
try:
    order_service = OrderAtOnceService()
    logger.info("Order At Once 서비스 초기화 완료 (텍스트 입력 전용)")
except ValueError as e:
    logger.error(f"Order At Once 서비스 초기화 실패: {e}")
    order_service = None


@router.post("/process", response_model=ProcessFlatResponse, summary="텍스트만 받아 메뉴/수량/포장여부 추출")
async def process_order_text(payload: ProcessTextRequest):
    """
    음성파일은 받지 않습니다. 이미 STT로 변환된 **text**만 입력받아
    메뉴/수량/포장여부 3가지만 평면 구조로 반환합니다.
    """
    if not order_service:
        raise HTTPException(status_code=500, detail="한번에 주문 서비스가 초기화되지 않았습니다.")

    # 언어 검증 (내부 룰/사전 선택 등에 사용 가능)
    lang = (payload.lang or "Kor").strip()
    validate_language(lang)

    text = (payload.text or "").strip()
    if not text:
        raise HTTPException(status_code=422, detail="text는 비어 있을 수 없습니다.")

    try:
        logger.info(f"[ORDER_TEXT] 입력: {text[:80]}{'...' if len(text) > 80 else ''}")

        # 서비스 호출 (결과 예: {"menu": {"name":"아이스 아메리카노"}, "quantity":2, "packaging":{"type":"포장"}})
        result = await order_service.process_order_text(text)

        # 안전 추출(서비스 반환 스키마에 따라 유연 처리)
        menu_name = ""
        if isinstance(result, dict):
            menu_val = result.get("menu")
            if isinstance(menu_val, dict):
                menu_name = (menu_val.get("name") or "").strip()
            elif isinstance(menu_val, str):
                menu_name = menu_val.strip()

        quantity = 1
        if isinstance(result, dict):
            q = result.get("quantity")
            if isinstance(q, (int, float, str)) and str(q).isdigit():
                quantity = int(q)

        packaging = "매장식사"
        if isinstance(result, dict):
            pack_val = result.get("packaging")
            if isinstance(pack_val, dict):
                packaging = (pack_val.get("type") or packaging).strip()
            elif isinstance(pack_val, str) and pack_val.strip():
                packaging = pack_val.strip()

        resp = {
            "success": True,
            "menu": menu_name,
            "quantity": int(quantity),
            "packaging": packaging
        }
        return JSONResponse(content=resp)

    except Exception as e:
        logger.error(f"[ORDER_TEXT] 처리 오류: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "menu": "", "quantity": 1, "packaging": "매장식사"}
        )


# ===== 유사도 검색(기존 유지) =====
@router.get("/menu-similarity/{menu_name}")
async def get_menu_similarity(menu_name: str):
    if not order_service:
        raise HTTPException(status_code=500, detail="한번에 주문 서비스가 초기화되지 않았습니다.")
    try:
        similar_menus = await order_service.find_similar_menu(menu_name)
        return JSONResponse(content={
            "success": True,
            "query": menu_name,
            "similar_menus": similar_menus or []
        })
    except Exception as e:
        logger.error(f"메뉴 유사도 검색 오류: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": f"검색 중 오류: {str(e)}"}
        )
