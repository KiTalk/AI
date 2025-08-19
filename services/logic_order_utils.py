import logging
from typing import Dict, Any, List, Tuple
from .redis_session_service import redis_session_manager
from core.exceptions.logic_exceptions import (
    MenuNotFoundException,
    OrderParsingException
)
from core.exceptions.session_exceptions import (
    SessionNotFoundException,
    InvalidSessionStepException,
)

logger = logging.getLogger(__name__)

# 세션 검증 및 반환
def validate_session(session_id: str, required_step: str = None) -> Dict[str, Any]:
    session = redis_session_manager.get_session(session_id)
    if not session:
        raise SessionNotFoundException(session_id)

    if required_step and session["step"] != required_step:
        raise InvalidSessionStepException(session["step"], required_step)

    return session

# 총 아이템 수와 총 가격 계산
def calculate_totals(orders: List[Dict[str, Any]]) -> Tuple[int, int]:
    total_items = sum(order["quantity"] for order in orders)
    total_price = sum(order["price"] * order["quantity"] for order in orders)
    return total_items, total_price

# 세션 주문 정보 업데이트
def update_session_orders(session_id: str, orders: List[Dict[str, Any]], step: str = "packaging") -> bool:
    total_items, _ = calculate_totals(orders)

    return redis_session_manager.update_session(
        session_id,
        step,
        {
            "orders": orders,
            "total_items": total_items,
            "menu_item": None,
            "quantity": None
        }
    )

# 메뉴 검증 및 주문 항목 생성
def validate_and_create_order_item(menu_item: str, quantity: int, search_menu_func) -> Dict[str, Any]:
    if quantity <= 0:
        raise OrderParsingException(f"'{menu_item}' 수량은 1개 이상이어야 합니다.")

    try:
        menu_info = search_menu_func(menu_item)
    except MenuNotFoundException:
        raise MenuNotFoundException(f"'{menu_item}' 메뉴를 찾을 수 없습니다.")

    return {
        "menu_item": menu_info["menu_item"],
        "price": menu_info["price"],
        "quantity": quantity,
        "original": f"{menu_item} {quantity}개"
    }

# 주문 목록을 문자열로 포맷팅
def format_order_list(orders: List[Dict[str, Any]]) -> str:
    return ', '.join([f"'{order['menu_item']}' {order['quantity']}개" for order in orders])

# 주문 목록 유효성 검사
def validate_order_list(orders: List[Dict[str, Any]]) -> None:
    if not orders:
        raise OrderParsingException("최소 1개 이상의 주문이 필요합니다.")

# 기존 주문 목록에 새로운 주문들을 추가
def add_new_orders(existing_orders: List[Dict[str, Any]], new_orders: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    updated_orders = [order.copy() for order in existing_orders]
    updated_orders.extend(new_orders)
    return updated_orders

# 특정 메뉴를 주문 목록에서 제거
def remove_order_by_menu_item(orders: List[Dict[str, Any]], menu_item: str) -> List[Dict[str, Any]]:
    original_count = len(orders)
    filtered_orders = [order for order in orders if order["menu_item"] != menu_item]

    if len(filtered_orders) == original_count:
        raise MenuNotFoundException(menu_item)

    if not filtered_orders:
        raise OrderParsingException("모든 주문을 삭제할 수 없습니다. 최소 1개 이상의 주문이 필요합니다.")

    return filtered_orders


def create_order_response(message: str, orders: List[Dict[str, Any]]) -> Dict[str, Any]:
    total_items, total_price = calculate_totals(orders)

    return {
        "message": message,
        "orders": orders,
        "total_items": total_items,
        "total_price": total_price
    }