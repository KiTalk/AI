from fastapi import APIRouter
from services.logic_service import process_menu
from models.logic_model import MenuRequest

router = APIRouter(
    prefix="/logic",
    tags=["logic"]
)

@router.post("/menu")
async def choose_menu(menu: MenuRequest):
    msg = process_menu(menu.menu_item)
    return {"message": msg, "next_step": "수량을 말씀해주세요"}

