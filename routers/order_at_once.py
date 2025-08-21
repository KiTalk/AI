from fastapi import APIRouter, HTTPException, Depends
from config.naver_stt_settings import logger
from models.order_response_models import StandardResponse, ErrorResponse, PackagingType

from services.order_at_once_service import OrderAtOnceService
from services.redis_session_service import session_manager

router = APIRouter(prefix="/order-at-once", tags=["Order At Once"])

def get_order_service() -> OrderAtOnceService:
    return OrderAtOnceService()

@router.post("/start", summary="세션 생성")
async def start_order_at_once():
    try:
        session_id = session_manager.create_session()
        return {"message": "한 번에 주문해주세요.", "session_id": session_id}
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

    menu_info = order_result.get("menu", {}) or {}

    if not menu_info.get("name"):
        return ErrorResponse(message="메뉴를 인식할 수 없습니다. 다시 말씀해주세요.", session_id=session_id)

    menu = order_result["menu"]
    qty = int(menu.get("quantity") or 0)
    price = int(menu.get("price") or 0)
    packaging = order_result.get("packaging") or None
    pack_enum = PackagingType(packaging) if packaging in {"포장", "매장식사"} else None

    return StandardResponse(
        message="주문이 완료되었습니다",
        order={
          "menu_id": menu.get("menu_id"),
          "menu_item": menu.get("name"),
          "price": price,
          "quantity": qty,
          "original": order_result.get("original_text", text),
          "popular": bool(menu.get("popular", False)),
          "temp": menu.get("temp"),
        },
        total_items=qty,
        total_price=qty * price,
        packaging=pack_enum,
        session_id=order_result.get("session_id", session_id),
        next_step=None
    )


@router.get("/session/{session_id}", summary="Redis 세션 조회")
async def get_session_order(session_id: str):
  try:
    session = session_manager.get_session(session_id)
    if not session:
      return ErrorResponse(
          message="세션을 찾을 수 없습니다.",
          session_id=session_id
      )

    data = session.get("data", {})
    order_at_once = data.get("order_at_once", {})

    menu_item = data.get("menu_item", "")
    if not menu_item:
      return ErrorResponse(
          message="주문 정보가 없습니다.",
          session_id=session_id
      )

    menu_id = data.get("menu_id")
    quantity = data.get("quantity", 1)
    price = order_at_once.get("price", 0) or 0
    packaging = data.get("packaging_type") or None
    pack_enum = PackagingType(packaging) if packaging in {"포장", "매장식사"} else None

    return {
      "message": "세션 조회 완료",
      "order": {
        "menu_id": menu_id,
        "menu_item": menu_item,
        "price": price,
        "quantity": quantity,
        "original": order_at_once.get("original_text", ""),
        "popular": bool(order_at_once.get("popular", False)),
        "temp": order_at_once.get("temp", "")
      },
      "total_items": quantity,
      "total_price": price * quantity,
      "packaging": pack_enum,
      "session_id": session_id,
      "next_step": None
    }

  except Exception as e:
    logger.error(f"세션 조회 오류: {e}")
    return ErrorResponse(
        message=f"세션 조회 실패: {str(e)}",
        session_id=session_id
    )