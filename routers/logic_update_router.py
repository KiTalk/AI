from fastapi import APIRouter, HTTPException, status
import logging
from models.logic_update_response import (
    UpdateAllOrdersRequest,
    AddOrderRequest,
    RemoveOrderRequest,
    OrderManagementResponse
)
from services.logic_update_service import (
    patch_orders,
    add_additional_order,
    remove_order_item
)
from core.exceptions.logic_exceptions import (
    MenuNotFoundException,
    OrderParsingException
)
from core.exceptions.session_exceptions import (
    SessionNotFoundException,
    InvalidSessionStepException,
    SessionUpdateFailedException
)

# 로거 설정
logger = logging.getLogger(__name__)

# Router 생성
router = APIRouter(prefix="/orders", tags=["Order Management"])


# 1. 부분 주문 업데이트 (PUT 메서드)
@router.put("/{session_id}/patch-update", response_model=OrderManagementResponse)
async def update_all_orders_endpoint(session_id: str, request: UpdateAllOrdersRequest) -> OrderManagementResponse:
    try:
        # Pydantic 모델을 딕셔너리 리스트로 변환
        order_items = [order.dict() for order in request.orders]

        result = patch_orders(
            session_id=session_id,
            order_items=order_items
        )

        return OrderManagementResponse(
            success=True,
            message=result["message"],
            orders=result["orders"],
            total_items=result["total_items"],
            total_price=result["total_price"]
        )

    except (SessionNotFoundException, InvalidSessionStepException,
            MenuNotFoundException, OrderParsingException, SessionUpdateFailedException):
        raise

    except Exception as e:
        logger.error(f"예상치 못한 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="서버 내부 오류가 발생했습니다"
        )


# 2. 추가 주문 (POST 메서드)
@router.post("/{session_id}/add", response_model=OrderManagementResponse)
async def add_order(session_id: str, request: AddOrderRequest) -> OrderManagementResponse:
    try:
        result = add_additional_order(
            session_id=session_id,
            order_text=request.order_text
        )

        return OrderManagementResponse(
            success=True,
            message=result["message"],
            orders=result["orders"],
            total_items=result["total_items"],
            total_price=result["total_price"]
        )

    except (SessionNotFoundException, InvalidSessionStepException,
            MenuNotFoundException, OrderParsingException, SessionUpdateFailedException):
        raise

    except Exception as e:
        logger.error(f"예상치 못한 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="서버 내부 오류가 발생했습니다"
        )


# 3. 주문 삭제 (DELETE 메서드)
@router.delete("/{session_id}/remove", response_model=OrderManagementResponse)
async def remove_order(session_id: str, request: RemoveOrderRequest) -> OrderManagementResponse:
    try:
        result = remove_order_item(
            session_id=session_id,  # 수정: request.session_id → session_id
            menu_item=request.menu_item
        )

        return OrderManagementResponse(
            success=True,
            message=result["message"],
            orders=result["orders"],
            total_items=result["total_items"],
            total_price=result["total_price"]
        )

    except (SessionNotFoundException, InvalidSessionStepException,
            MenuNotFoundException, OrderParsingException, SessionUpdateFailedException):
        raise

    except Exception as e:
        logger.error(f"예상치 못한 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="서버 내부 오류가 발생했습니다"
        )