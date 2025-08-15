from fastapi import APIRouter, HTTPException
from services.logic_service import process_menu, process_quantity
from models.logic_model import MenuRequest, QuantityRequest

router = APIRouter(
    prefix="/logic",
    tags=["logic"]
)

@router.post("/menu")
async def choose_menu(menu: MenuRequest):
    msg = process_menu(menu.menu_item)
    return {"message": msg, "next_step": "수량을 말씀해주세요"}

@router.post("/quantity")
async def choose_quantity(q: QuantityRequest):
    try:
        msg = process_quantity(q.quantity)
        return {"quantity": msg, "next_step": "포장/매장식사를 말씀해주세요"}
    except HTTPException as e:
        return {
            "message": e.detail,
            "next_step": "수량을 다시 말씀해주세요", #같은 단계
            "current_step": "quantity", #현재 단계
            "retry": True  # 재시도
        }