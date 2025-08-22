from fastapi import APIRouter, Depends, Query, HTTPException
from typing import List, Optional, Literal
from starlette import status
from core.common.security import get_current_owner
from schemas.orders import OrderOut, OrderStatusUpdateRes
from services.owner_order_service import (
    service_list_orders,
    service_mark_completed,
    service_mark_paid,
    NotFoundError,
    ConflictError,
)

router = APIRouter(prefix="/owner", tags=["Owner Orders"])

@router.get(
    "/orders",
    response_model=List[OrderOut],
    summary="주문 내역 조회(점주 전용)"
)
def owner_list_orders(
    status_filter: Optional[Literal["PAID", "COMPLETED"]] = Query(
        None, alias="status", description="옵션: 'PAID' 또는 'COMPLETED' (기본: 둘 다)"
    ),
    _owner = Depends(get_current_owner),
):
    return service_list_orders(status=status_filter)

@router.patch(
    "/orders/{order_id}/mark-completed",
    response_model=OrderStatusUpdateRes,
    summary="주문 상태를 COMPLETED로 변경"
)
def owner_mark_completed(order_id: int, _owner = Depends(get_current_owner)):
    try:
        result = service_mark_completed(order_id)
        return result
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ConflictError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

@router.patch(
    "/orders/{order_id}/mark-paid",
    response_model=OrderStatusUpdateRes,
    summary="주문 상태를 PAID로 변경"
)
def owner_mark_paid(order_id: int, _owner = Depends(get_current_owner)):
    try:
        result = service_mark_paid(order_id)
        return result
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ConflictError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
