from fastapi import APIRouter, HTTPException
from services.logic_service import process_order, process_packaging, analyze_confirmation, add_profiles_to_orders
from models.logic_request_models import MenuRequest, PackagingRequest
from models.logic_response_models import StandardResponse, ErrorResponse, SessionResponse

from services.redis_session_service import session_manager
import logging

from core.exceptions.session_exceptions import (
    SessionNotFoundException,
    InvalidSessionStepException,
    SessionUpdateFailedException
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/logic",
    tags=["logic"]
)

# 세션 생성
@router.post("/start", summary="세션 생성")
async def start_order():
    session_id = session_manager.create_session()
    return StandardResponse(
        message="주문을 시작합니다. 원하시는 메뉴와 수량을 말씀해주세요.",
        session_id=session_id,
        next_step="메뉴와 수량 입력"
    )

@router.post("/order/{session_id}", summary="메뉴/수량 처리")
async def place_order(session_id: str, order: MenuRequest):  # MenuRequest 재사용
    try:
        msg = process_order(session_id, order.menu_item)

        logger.debug(f"주문 처리 완료: {session_id}")
        logger.debug(f"현재 단계: packaging, 다음: 포장/매장식사 선택")

        return StandardResponse(
            message=msg["message"],
            orders=msg["orders"],
            total_items=msg["total_items"],
            total_price=msg["total_price"],
            packaging=None,
            session_id=session_id,
            next_step="포장/매장식사 선택"
        )
    
    except SessionNotFoundException as e:
        return ErrorResponse(
            message=e.detail,
            session_id=session_id,
            next_step="새로운 세션으로 시작해주세요"
        )
    except InvalidSessionStepException as e:
        return ErrorResponse(
            message=e.detail,
            session_id=session_id,
            next_step="올바른 단계에서 주문해주세요"
        )
    except SessionUpdateFailedException as e:
        return ErrorResponse(
            message=e.detail,
            session_id=session_id,
            next_step="다시 시도해주세요"
        )
    except HTTPException as e:
        return ErrorResponse(
            message=e.detail,
            session_id=session_id,
            next_step="메뉴와 수량을 다시 말씀해주세요"
        )

@router.post("/packaging/{session_id}", summary="매장/포장 처리")
async def choose_packaging(session_id: str, p: PackagingRequest):
    try:
        msg = process_packaging(session_id, p.packaging_type)

        session = session_manager.get_session(session_id)
        orders = session["data"].get("orders", [])
        total_items = session["data"].get("total_items", 0)
        total_price = sum(order["price"] * order["quantity"] for order in orders) if orders else 0

        logger.debug(f"처리 완료: {session_id} - {msg}")

        return StandardResponse(
            message=f"주문이 완료되었습니다. {msg}",
            orders=orders,
            total_items=total_items,
            total_price=total_price,
            packaging=msg,
            session_id=session_id,
            next_step="주문 완료"
        )
    except HTTPException as e:
        return ErrorResponse(
            message=e.detail,
            session_id=session_id,
            next_step="포장 방식을 다시 선택"
        )

# 전체 세션 정보 조회
@router.get("/session/{session_id}", summary="Redis에 저장된 세션 조회")
async def get_full_session(session_id: str):
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")

    orders = add_profiles_to_orders(session_id)
    total_items = session["data"].get("total_items", 0)
    total_price = sum(order["price"] * order["quantity"] for order in orders) if orders else 0
    packaging = session["data"].get("packaging_type")

    logger.debug(f"세션 조회 완료: {session_id} - {len(orders)}개 주문, {total_price}원")

    return SessionResponse(
        message="세션 조회 완료",
        orders=orders,
        total_items=total_items,
        total_price=total_price,
        packaging=packaging,
        session_id=session_id
    )

# 확인 응답 처리
@router.post("/confirm", summary="확인 응답 처리")
async def process_confirmation(request: MenuRequest):
    try:
        is_confirmed = analyze_confirmation(request.menu_item)

        return {
            "message": "응답이 처리되었습니다.",
            "confirmed": is_confirmed
        }

    except Exception as e:
        logger.error(f"확인 응답 처리 중 오류: {e}")
        return {
            "message": "응답 처리 중 오류가 발생했습니다.",
            "confirmed": False
        }