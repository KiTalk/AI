from fastapi import APIRouter, HTTPException
from services.logic_service import process_menu, process_quantity
from models.logic_model import StartOrderRequest, MenuRequest, QuantityRequest
from services.redis_session_service import session_manager

router = APIRouter(
    prefix="/logic",
    tags=["logic"]
)

# 세션 생성
@router.post("/start")
async def start_order():
    session_id = session_manager.create_session()
    return {
        "message": "주문을 시작합니다. 원하시는 메뉴를 말씀해주세요.",
        "session_id": session_id,
        "current_step": "menu",
        "next_step": "메뉴 선택"
    }

@router.post("/menu/{session_id}")
async def choose_menu(session_id: str, menu: MenuRequest):
    try:
        msg = process_menu(session_id, menu.menu_item)
        return {
            "menu": msg,
            "session_id": session_id,
            "current_step": "quantity", # 다음에 해야할 단계
            "next_step": "수량 선택"
        }
    except HTTPException as e:
        return {
            "message": e.detail,
            "session_id": session_id,
            "current_step": "menu",
            "next_step": "메뉴를 다시 선택",
            "retry": True
        }

@router.post("/quantity/{session_id}")
async def choose_quantity(session_id, q: QuantityRequest):
    try:
        msg = process_quantity(session_id, q.quantity)
        return {
            "quantity": msg,
            "session_id": session_id,
            "current_step": "packaging",
            "next_step": "포장/매장식사 선택"
        }
    except HTTPException as e:
        return {
            "message": e.detail,
            "session_id": session_id,
            "current_step": "quantity",
            "next_step": "수량 다시 선택", #같은 단계
            "retry": True  # 재시도
        }