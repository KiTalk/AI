import logging
from typing import Dict, Any, List
from .logic_service import (
    split_multiple_orders,
    validate_single_order_simplified,
    search_menu
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
from .logic_order_utils import (
    validate_session,
    validate_and_create_order_item,
    validate_order_list,
    update_session_orders,
    format_order_list,
    create_order_response,
    add_new_orders,
    remove_order_by_menu_item,
    compare_orders,
    generate_update_message
)

logger = logging.getLogger(__name__)

# 전체 주문 부분적 업데이트 함수
def patch_orders(session_id: str, order_items: List[Dict[str, Any]]) -> Dict[str, Any]:
    try:
        session = validate_session(session_id, "packaging")

        # 기존 주문 목록 조회
        existing_orders = session["data"]["orders"]

        # 새로운 주문 목록 생성 및 검증
        new_orders = []
        for item in order_items:
            order_item = validate_and_create_order_item(
                item["menu_item"],
                item["quantity"],
                search_menu
            )
            new_orders.append(order_item)

        validate_order_list(new_orders)

        # 변경사항 감지
        changes = compare_orders(existing_orders, new_orders)

        # 변경사항이 있는 경우에만 업데이트
        if changes["has_changes"]:
            success = update_session_orders(session_id, new_orders)
            if not success:
                raise SessionUpdateFailedException(session_id, "주문 업데이트")

        # 변경사항 메시지 생성
        message = generate_update_message(changes)
        return create_order_response(message, new_orders)

    except (SessionNotFoundException, InvalidSessionStepException,
            SessionUpdateFailedException, MenuNotFoundException, OrderParsingException):
        raise
    except Exception as e:
        logger.error(f"주문 업데이트 중 오류: {e}")
        raise OrderParsingException("주문 업데이트 중 오류가 발생했습니다")

# 기존 주문에 새로운 메뉴 추가
def add_additional_order(session_id: str, order_text: str) -> Dict[str, Any]:
    try:
        # 세션 검증
        session = validate_session(session_id, "packaging")

        # 새로운 주문 파싱
        individual_orders = split_multiple_orders(order_text)
        new_orders = []

        for order in individual_orders:
            try:
                validated_order = validate_single_order_simplified(order)
                new_orders.append(validated_order)
            except MenuNotFoundException as e:
                raise e

        # 기존 주문에 새 주문들 단순 추가 (중복 체크 없음)
        existing_orders = session["data"]["orders"]
        updated_orders = add_new_orders(existing_orders, new_orders)

        # 세션 업데이트
        success = update_session_orders(session_id, updated_orders)
        if not success:
            raise SessionUpdateFailedException(session_id, "추가 주문 업데이트")

        # 응답 생성
        message = f"다음 메뉴가 추가되었습니다: {format_order_list(new_orders)}"
        return create_order_response(message, updated_orders)

    except (SessionNotFoundException, InvalidSessionStepException,
            SessionUpdateFailedException, MenuNotFoundException, OrderParsingException):
        raise
    except Exception as e:
        logger.error(f"추가 주문 처리 중 오류: {e}")
        raise OrderParsingException("추가 주문 처리 중 오류가 발생했습니다")

# 특정 메뉴를 주문에서 완전히 삭제
def remove_order_item(session_id: str, menu_item: str) -> Dict[str, Any]:
    try:
        # 세션 검증
        session = validate_session(session_id, "packaging")

        # 메뉴 제거
        orders = session["data"]["orders"]
        filtered_orders = remove_order_by_menu_item(orders, menu_item)

        # 세션 업데이트
        success = update_session_orders(session_id, filtered_orders)
        if not success:
            raise SessionUpdateFailedException(session_id, "주문 항목 삭제")

        # 응답 생성
        message = f"'{menu_item}'이(가) 주문에서 삭제되었습니다."
        return create_order_response(message, filtered_orders)

    except (SessionNotFoundException, InvalidSessionStepException,
            SessionUpdateFailedException, MenuNotFoundException, OrderParsingException):
        raise
    except Exception as e:
        logger.error(f"주문 항목 삭제 중 오류: {e}")
        raise OrderParsingException("주문 항목 삭제 중 오류가 발생했습니다")