import logging
from typing import Dict, Any, List, Tuple
from .redis_session_service import redis_session_manager
from fuzzywuzzy import fuzz
from sentence_transformers import SentenceTransformer
from core.exceptions.logic_exceptions import (
    MenuNotFoundException,
    OrderParsingException
)
from core.exceptions.session_exceptions import (
    SessionNotFoundException,
    InvalidSessionStepException,
)

model = SentenceTransformer('jhgan/ko-sroberta-multitask')

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
    if quantity < 0:
        raise OrderParsingException(f"'{menu_item}' 수량은 1개 이상이어야 합니다.")

    try:
        menu_info = search_menu_func(menu_item)
    except MenuNotFoundException:
        raise MenuNotFoundException(f"'{menu_item}' 메뉴를 찾을 수 없습니다.")

    return {
        "menu_item": menu_info["menu_item"],
        "price": menu_info["price"],
        "quantity": quantity,
        "original": f"{menu_item} {quantity}개",
        "popular": menu_info["popular"],
        "temp": menu_info["temp"]
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

# 기존 주문과 새 주문을 비교하여 변경사항 반환
def compare_orders(existing_orders: List[Dict], new_orders: List[Dict]) -> Dict:
    existing_dict = {order["menu_item"]: order["quantity"] for order in existing_orders}
    new_dict = {order["menu_item"]: order["quantity"] for order in new_orders}

    added = []
    modified = []
    removed = []

    # 추가되거나 수정된 항목 찾기
    for menu_item, quantity in new_dict.items():
        if menu_item not in existing_dict:
            added.append({"menu_item": menu_item, "quantity": quantity})
        elif existing_dict[menu_item] != quantity:
            modified.append({
                "menu_item": menu_item,
                "old_quantity": existing_dict[menu_item],
                "new_quantity": quantity
            })

    # 삭제된 항목 찾기
    for menu_item in existing_dict:
        if menu_item not in new_dict:
            removed.append({"menu_item": menu_item, "quantity": existing_dict[menu_item]})

    return {
        "has_changes": bool(added or modified or removed),
        "added": added,
        "modified": modified,
        "removed": removed
    }

# 변경사항을 기반으로 메시지 생성
def generate_update_message(changes: Dict) -> str:
    if not changes["has_changes"]:
        return "주문에 변경사항이 없습니다."

    messages = []

    if changes["added"]:
        added_items = [f"{item['menu_item']} {item['quantity']}개" for item in changes["added"]]
        messages.append(f"추가: {', '.join(added_items)}")

    if changes["modified"]:
        modified_items = [f"{item['menu_item']} {item['old_quantity']}개 → {item['new_quantity']}개"
                          for item in changes["modified"]]
        messages.append(f"수량변경: {', '.join(modified_items)}")

    if changes["removed"]:
        removed_items = [f"{item['menu_item']} {item['quantity']}개" for item in changes["removed"]]
        messages.append(f"삭제: {', '.join(removed_items)}")

    return "주문이 업데이트되었습니다. " + " | ".join(messages)

# 벡터 + fuzzy 유사도 점수 계산
def calculate_similarity_score(input_text: str, target_text: str, threshold: float = 0.45) -> Tuple[
    float, float, float]:

    # 1. 벡터 유사도 계산
    input_vector = model.encode([input_text.lower()])[0]
    target_vector = model.encode([target_text.lower()])[0]

    import numpy as np
    dot_product = float(np.dot(input_vector, target_vector))
    norm_product = float(np.linalg.norm(input_vector) * np.linalg.norm(target_vector))
    vector_score = dot_product / norm_product

    # 2. fuzzy 점수 계산
    ratio_score = fuzz.ratio(target_text, input_text.lower()) / 100
    partial_score = fuzz.partial_ratio(target_text, input_text.lower()) / 100
    token_score = fuzz.token_sort_ratio(target_text, input_text.lower()) / 100
    best_fuzzy = max(ratio_score, partial_score, token_score)

    # 3. 결합 점수
    final_score = 0.7 * vector_score + 0.3 * best_fuzzy

    return final_score, vector_score, best_fuzzy