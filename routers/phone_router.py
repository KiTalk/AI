from typing import Union
from fastapi import APIRouter, HTTPException, status
import logging

from models.phone_request_models import PhoneChoiceRequest, PhoneInputRequest
from models.phone_response_models import PhoneChoiceResponse, OrderCompleteResponse
from services.phone_service import process_phone_choice, process_phone_input
from core.exceptions.session_exceptions import (
    SessionNotFoundException,
    InvalidSessionStepException,
    SessionUpdateFailedException
)
from core.exceptions.logic_exceptions import OrderParsingException

logger = logging.getLogger(__name__)

# 전화번호 관련 라우터
router = APIRouter(
    prefix="/api/phone",
    tags=["phone"],
    responses={
        404: {"description": "Session not found"},
        400: {"description": "Invalid request"},
        500: {"description": "Internal server error"}
    }
)

# 전화번호 입력 여부 선택
@router.post("/choice/{session_id}", response_model=Union[PhoneChoiceResponse], summary="전화번호 입력 여부 선택")
async def phone_choice(
    session_id: str,
    request: PhoneChoiceRequest
) -> Union[PhoneChoiceResponse, OrderCompleteResponse]:
    try:
        result = process_phone_choice(session_id, request.wants_phone)
        
        if request.wants_phone:
            # 전화번호 입력하겠다고 선택한 경우
            return PhoneChoiceResponse(
                message=result["message"],
                session_id=session_id,
                next_step=result["next_step"]
            )
        else:
            # 전화번호 입력 안하고 바로 완료하는 경우
            return OrderCompleteResponse(
                message=result["message"],
                order_id=result["order_id"],
                orders=result["orders"],
                total_items=result["total_items"],
                total_price=result["total_price"],
                packaging=result["packaging"],
                phone_number=result["phone_number"],
                session_id=session_id,
                next_step=result["next_step"]
            )
    
    except SessionNotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"세션을 찾을 수 없습니다: {session_id}"
        )
    except InvalidSessionStepException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"잘못된 세션 단계입니다. 현재: {e.current_step}, 필요: {e.required_step}"
        )
    except SessionUpdateFailedException:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="세션 업데이트에 실패했습니다"
        )
    except OrderParsingException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"전화번호 선택 처리 중 예상치 못한 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="내부 서버 오류가 발생했습니다"
        )

# 전화번호 입력
@router.post("/input/{session_id}", response_model=OrderCompleteResponse, summary="전화번호 입력 및 주문완료")
async def phone_input(
    session_id: str,
    request: PhoneInputRequest
) -> OrderCompleteResponse:
    try:
        result = process_phone_input(session_id, request.phone_number)
        
        return OrderCompleteResponse(
            message=result["message"],
            order_id=result["order_id"],
            orders=result["orders"],
            total_items=result["total_items"],
            total_price=result["total_price"],
            packaging=result["packaging"],
            phone_number=result["phone_number"],
            session_id=session_id,
            next_step=result["next_step"]
        )
    
    except SessionNotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"세션을 찾을 수 없습니다: {session_id}"
        )
    except InvalidSessionStepException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"잘못된 세션 단계입니다. 현재: {e.current_step}, 필요: {e.required_step}"
        )
    except SessionUpdateFailedException:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="세션 업데이트에 실패했습니다"
        )
    except OrderParsingException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"전화번호 입력 처리 중 예상치 못한 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="내부 서버 오류가 발생했습니다"
        )
