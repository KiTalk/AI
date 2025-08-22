import logging
from typing import Dict, Any, List
from .logic_service import (
    split_multiple_orders,
    validate_single_order_simplified,
    search_menu
)
from services.similarity_utils import warmup_embeddings
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
        try:
            session = validate_session(session_id, "packaging")
        except InvalidSessionStepException:
            session = validate_session(session_id, "completed")

        # 기존 주문 목록 조회 - 안전하게 처리
        session_data = session.get("data", {})

        # 기존 주문 목록 조회
        if "order_at_once" in session_data:
            # order-at-once에서 온 세션의 경우
            existing_orders = []  # 빈 리스트로 초기화하거나
            # 또는 order_at_once 데이터를 orders 형태로 변환
        else:
            # 일반적인 경우
            existing_orders = session_data.get("orders", [])

        menu_names = [item["menu_item"] for item in order_items]
        if menu_names:
            warmup_embeddings(menu_names)

        # 새로운 주문 목록 생성 및 검증
        new_orders = []
        for item in order_items:
            order_item = validate_and_create_order_item(
                item["menu_item"],
                item["quantity"],
                search_menu
            )
            order_item["temp"] = item["temp"]
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

        menu_texts = []
        for order in individual_orders:
            try:
                # 간단한 메뉴명 추출 (validate 전에 예열용)
                # 정확한 추출은 validate_single_order_simplified에서 수행
                words = order.strip().split()
                if words:
                    menu_texts.extend(words)  # 단어별로 추가
            except:
                continue  # 예열 실패는 무시

        # 배치 임베딩 예열
        if menu_texts:
            warmup_embeddings(menu_texts)

        new_orders = []

        for order in individual_orders:
            try:
                validated_order = validate_single_order_simplified(order)
                new_orders.append(validated_order)
            except MenuNotFoundException as e:
                logger.warning(f"메뉴를 찾을 수 없음: {order}")
                raise MenuNotFoundException(f"'{order}' 메뉴를 찾을 수 없습니다. 메뉴명을 다시 확인해주세요.")

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
def remove_order_item(session_id: str, menu_id: int) -> Dict[str, Any]:
    try:
        # 세션 검증
        session = validate_session(session_id, "packaging")

        # 메뉴 제거
        orders = session["data"]["orders"]
        if not orders:
            raise OrderParsingException("삭제할 주문이 없습니다.")

        menu_exists = any(order["menu_id"] == menu_id for order in orders)
        if not menu_exists:
            existing_menu_ids = [order["menu_id"] for order in orders]
            logger.info(f"삭제하려는 menu_id '{menu_id}'가 주문에 없음. 기존 menu_id: {existing_menu_ids}")
            raise MenuNotFoundException(f"menu_id {menu_id}에 해당하는 주문이 없습니다.")

        deleted_menu = next(order["menu_item"] for order in orders if order["menu_id"] == menu_id)

        filtered_orders = [order for order in orders if order["menu_id"] != menu_id]

        # 세션 업데이트
        success = update_session_orders(session_id, filtered_orders)
        if not success:
            raise SessionUpdateFailedException(session_id, "주문 항목 삭제")

        # 응답 생성
        message = f"'{deleted_menu}'이(가) 주문에서 삭제되었습니다."
        return create_order_response(message, filtered_orders)

    except (SessionNotFoundException, InvalidSessionStepException,
            SessionUpdateFailedException, MenuNotFoundException, OrderParsingException):
        raise
    except Exception as e:
        logger.error(f"주문 항목 삭제 중 오류: {e}")
        raise OrderParsingException("주문 항목 삭제 중 오류가 발생했습니다")

# 전체 주문 삭제 (주문 초기화)
def clear_all_orders(session_id: str) -> Dict[str, Any]:
    try:
        # 세션 검증
        session = validate_session(session_id, "packaging")

        # 현재 주문 확인
        orders = session["data"]["orders"]
        if not orders:
            raise OrderParsingException("삭제할 주문이 없습니다.")

        # 빈 주문 목록으로 업데이트
        empty_orders = []
        success = update_session_orders(session_id, empty_orders)
        if not success:
            raise SessionUpdateFailedException(session_id, "전체 주문 삭제")

        # 응답 생성
        message = "모든 주문이 삭제되었습니다."
        return create_order_response(message, empty_orders)

    except (SessionNotFoundException, InvalidSessionStepException,
            SessionUpdateFailedException, OrderParsingException):
        raise
    except Exception as e:
        logger.error(f"전체 주문 삭제 중 오류: {e}")
        raise OrderParsingException("전체 주문 삭제 중 오류가 발생했습니다")