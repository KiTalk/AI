from fastapi import APIRouter, HTTPException, Depends
from config.naver_stt_settings import logger
from models.order_response_models import StandardResponse, ErrorResponse

from services.order_at_once_service import OrderAtOnceService
from services.redis_session_service import session_manager

router = APIRouter(prefix="/order-at-once", tags=["Order At Once"])

def get_order_service() -> OrderAtOnceService:
    return OrderAtOnceService()

@router.post("/start", summary="세션 생성")
async def start_order_at_once():
    try:
        session_id = session_manager.create_session()
        return StandardResponse(message="한 번에 주문해주세요.", session_id=session_id)
    except Exception as e:
        logger.error(f"세션 생성 중 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"세션 생성 실패: {str(e)}")


@router.post("/process/{session_id}", summary="한번에 주문 처리")
async def process_order_at_once(
    session_id: str,
    text: str,
    order_service: OrderAtOnceService = Depends(get_order_service),
):
    logger.info(f"한번에 주문 처리: {text}, 세션: {session_id}")

    try:
        order_result = await order_service.process_order_with_session(text, session_id)
    except Exception as e:
        logger.error(f"주문 처리 중 오류: {str(e)}")
        return ErrorResponse(message=f"주문 처리 중 오류: {str(e)}", session_id=session_id)

    menu_info = order_result.get("menu", {})
    menu_name = menu_info.get("name", "")
    packaging = order_result.get("packaging", "")

    if not menu_name:
        return ErrorResponse(message="메뉴를 인식할 수 없습니다. 다시 말씀해주세요.", session_id=session_id)

    result = StandardResponse(
        message="주문이 완료되었습니다.",
        session_id=session_id,
        debug={
            "success": True,
            "recognized_text": text,
            "menu_item": menu_name,
            "price": menu_info.get("price", 0),
            "quantity": menu_info.get("quantity", 1),
            "popular": (
                menu_info.get("popular", False)
                if menu_info.get("popular") is not None
                else ""
            ),
            "temp": menu_info.get("temp", ""),
            "packaging": packaging,
        },
    )

    logger.info(f"한번에 주문 처리 완료: {menu_name} {menu_info.get('quantity', 1)}개")
    return result
