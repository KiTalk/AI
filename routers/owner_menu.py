from typing import Annotated
from fastapi import APIRouter, UploadFile, File, Form, Depends
from core.common.security import get_current_owner
from schemas.owner_menu import OwnerMenuCreateResponse
from services.owner_menu_service import OwnerMenuService

router = APIRouter(prefix="/owner", tags=["Owner"])

@router.post(
    "/add-menu",
    response_model=OwnerMenuCreateResponse,
    status_code=201,
    summary="메뉴 추가(점주 전용)",
    dependencies=[Depends(get_current_owner)]
)
def add_menu(
    name: Annotated[str, Form(...)],
    temperature: Annotated[str, Form(..., pattern="^(hot|ice|none)$")],
    price: Annotated[int, Form(..., ge=0)],
    category: Annotated[str, Form(..., pattern="^(커피|스무디|버블티|주스|디저트|기타 음료|스페셜 티|에이드|차|프라페|특색 라떼)$")],
    popular: Annotated[bool, Form()] = False,  # 기본값은 '=' 로
    profile: Annotated[UploadFile | None, File(description="메뉴 이미지 파일(선택, image/* 만 허용)")] = None  # 기본값은 '=' 로
):
    return OwnerMenuService.create_menu_with_optional_image(
        name=name,
        temperature=temperature,
        price=price,
        category=category,
        popular=popular,
        profile_file=profile
    )
