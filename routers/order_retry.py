from fastapi import APIRouter, Depends, HTTPException

from config.naver_stt_settings import logger
from services.order_retry_service import OrderRetryService
from services.order_at_once_service import OrderAtOnceService

from models.order_retry_request_models import (
    PackagingRetryRequest,
    TempRetryRequest,
)
from models.order_retry_response_models import (
    PackagingRetryResponse,
    TempRetryResponse,
)

router = APIRouter(prefix="/order-retry", tags=["Order Retry"])

def get_retry_service() -> OrderRetryService:
    return OrderRetryService(base_service=OrderAtOnceService())

@router.post("/update-packaging/{session_id}", response_model=PackagingRetryResponse, summary="포장 여부 업데이트")
async def update_packaging_only(session_id: str, req: PackagingRetryRequest, svc: OrderRetryService = Depends(get_retry_service)):
    try:
        out = await svc.update_packaging_only(session_id, req.packaging)
        return PackagingRetryResponse(
            session_id=session_id,
            message="포장/매장 여부가 업데이트되었습니다.",
            packaging=out["packaging"]
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[order-retry/update-packaging] 오류: {e}")
        raise HTTPException(status_code=500, detail=f"포장/매장 여부 업데이트 실패: {str(e)}")

@router.post("/update-temp/{session_id}", response_model=TempRetryResponse, summary="음료 온도 업데이트")
async def update_temp_only(session_id: str, req: TempRetryRequest, svc: OrderRetryService = Depends(get_retry_service)):
    try:
        out = await svc.update_temp_only(session_id, req.temp)
        return TempRetryResponse(
            session_id=session_id,
            message="음료 온도가 업데이트되었습니다.",
            temp=out["temp"],
            menu_id=out.get("menu_id")
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[order-retry/update-temp] 오류: {e}")
        raise HTTPException(status_code=500, detail=f"온도 업데이트 실패: {str(e)}")
