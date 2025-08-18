from fastapi import APIRouter, HTTPException
from services.logic_service import process_order, process_packaging
from models.logic_model import MenuRequest, QuantityRequest, PackagingRequest
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
        "current_step": "menu_and_quantity",
        "next_step": "메뉴와 수량 입력"
    }

@router.post("/order/{session_id}")
async def place_order(session_id: str, order: MenuRequest):  # MenuRequest 재사용
    try:
        msg = process_order(session_id, order.menu_item)  # "라면 2그릇" 전체 처리
        return {
            "message": msg,
            "session_id": session_id,
            "current_step": "packaging",  # 바로 포장 단계로
            "next_step": "포장/매장식사 선택"
        }
    except HTTPException as e:
        return {
            "message": e.detail,
            "session_id": session_id,
            "current_step": "started",
            "next_step": "메뉴와 수량을 다시 말씀해주세요",
            "retry": True
        }

@router.post("/packaging/{session_id}")
async def choose_packaging(session_id: str, p: PackagingRequest):
    try:
        msg = process_packaging(session_id, p.packaging_type)
        return {
            "packaging": msg,
            "session_id": session_id,
            "current_step": "completed",
            "next_step": "주문 완료"
        }
    except HTTPException as e:
        return {
            "message": e.detail,
            "session_id": session_id,
            "current_step": "packaging",
            "next_step": "포장 방식을 다시 선택",
            "retry": True
        }

# 전체 세션 정보 조회
@router.get("/session/{session_id}")
async def get_full_session(session_id: str):
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")

    return {
        "session_id": session_id,
        "session_data": session
    }