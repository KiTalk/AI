from fastapi import HTTPException
from pyexpat.errors import messages
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer
from fuzzywuzzy import fuzz
import json
import os
import re
from typing import Tuple, List, Optional, Dict, Any
from .redis_session_service import redis_session_manager

# Qdrant 클라이언트 초기화
client = QdrantClient(url="http://localhost:6333")

# SentenceTransformer 모델 초기화
model = SentenceTransformer('jhgan/ko-sroberta-multitask')

def search_menu(menu_item: str) -> Dict[str, Any] | None:
    try:
        query_vector = model.encode([menu_item])[0]

        results = client.query_points(
            collection_name="menu",
            query=query_vector.tolist(),
            limit=3,
            score_threshold=0.2
        )

        if results.points:
            enhanced_results = []
            for result in results.points:
                menu_name = result.payload['menu_item']
                price = result.payload['price']
                vector_score = result.score

                # 여러 fuzzy 점수 계산
                ratio_score = fuzz.ratio(menu_item, menu_name) / 100
                partial_score = fuzz.partial_ratio(menu_item, menu_name) / 100
                token_score = fuzz.token_sort_ratio(menu_item, menu_name) / 100

                # 최고 fuzzy 점수 선택
                best_fuzzy = max(ratio_score, partial_score, token_score)

                # 결합 점수
                final_score = 0.7 * vector_score + 0.3 * best_fuzzy

                enhanced_results.append((menu_name, price, final_score, vector_score, best_fuzzy))

            enhanced_results.sort(key=lambda x: x[2], reverse=True)

            print(f"'{menu_item}' 실용적 검색:")
            for menu, price, final, vector, fuzzy in enhanced_results:
                print(f"  - {menu}({price}원): 최종={final:.3f} (벡터={vector:.3f}, Fuzzy={fuzzy:.3f})")

            if enhanced_results[0][2] >= 0.45:
                return {
                    "menu_item": enhanced_results[0][0],
                    "price": enhanced_results[0][1]
                }

    except Exception as e:
        print(f"검색 중 오류: {e}")

    return None

# 수량 패턴 설정
def load_quantity_config():
    try:
        config_dir = os.path.join(os.path.dirname(__file__), '..', 'config')
        config_file = os.path.join(config_dir, 'quantity_patterns.json')

        with open(config_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"설정 파일 로드 실패: {e}")
        return {}

# 자연어 수량 파싱 함수
def parse_quantity_from_text(text: str) -> Optional[int]:
    text = text.strip().lower()
    config = load_quantity_config()

    # 1. 아라비아 숫자 추출
    number_match = re.search(r'\d+', text)
    if number_match:
        return int(number_match.group())

    # 2. config 파일의 한글 숫자 확인
    korean_numbers = config["korean_numbers"]
    for korean_word in korean_numbers:
        if korean_word in text:
            return korean_numbers[korean_word]

    return None

# 메뉴와 수량을 함께 처리하는 함수
def process_order(session_id: str, order_text: str) -> Dict[str, Any]:
    # 세션 확인
    session = redis_session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="유효하지 않은 세션입니다.")

    # started 단계에서만 실행 가능
    if session["step"] != "started":
        raise HTTPException(status_code=400, detail="현재 주문 입력 단계가 아닙니다.")

    # 주문 분리
    individual_orders = split_multiple_orders(order_text)
    print(f"주문 분리: {individual_orders}")

    message = process_multiple_orders(session_id, individual_orders)
    updated_session = redis_session_manager.get_session(session_id)
    orders = updated_session["data"]["orders"]
    total_items = updated_session["data"]["total_items"]
    total_price = sum(order["price"] * order["quantity"] for order in orders)

    return {
        "message": message,
        "orders": orders,
        "total_items": total_items,
        "total_price": total_price
    }

# 개별 주문으로 분리
def split_multiple_orders(order_text: str) -> List[str]:
    config = load_quantity_config()

    # 1단계: config의 구분자로 분리 시도 (대비로 뒤에 예시 추가함)
    separators = config.get("separators", [",", "그리고", "하고", "랑", "와", "과"])
    pattern = '|'.join(re.escape(sep) for sep in separators)
    orders = re.split(pattern, order_text)
    orders = [order.strip() for order in orders if order.strip()]

    # 구분자로 분리되었으면 반환
    if len(orders) > 1:
        return orders

    # 2단계: 패턴 기반 자동 분리 (config 기반)
    units = config.get("units", ["개", "그릇", "잔", "인분", "마리", "판", "조각", "줄", "공기", "병"])
    korean_numbers = config.get("korean_numbers", {})

    # 동적으로 패턴 생성
    unit_pattern = '|'.join(re.escape(unit) for unit in units)
    korean_nums = '|'.join(re.escape(num) for num in korean_numbers.keys())
    quantity_pattern = rf'(\d+|{korean_nums})'

    # 전체 패턴: 메뉴명 + 수량 + 단위(선택)
    # 단위가 없어도 동작하도록 수정
    if config.get("unit_required", False):
        # 단위 필수
        full_pattern = rf'([가-힣\s]+?)\s*{quantity_pattern}\s*({unit_pattern})'
    else:
        # 단위 선택적
        full_pattern = rf'([가-힣\s]+?)\s*{quantity_pattern}\s*({unit_pattern})?'

    matches = re.findall(full_pattern, order_text)

    if len(matches) > 1:
        # 여러 개 매치되면 각각을 주문으로 재구성
        parsed_orders = []
        for match in matches:
            if len(match) == 3:  # (메뉴, 수량, 단위)
                menu, qty, unit = match
                if unit:
                    parsed_orders.append(f"{menu.strip()} {qty} {unit}")
                else:
                    parsed_orders.append(f"{menu.strip()} {qty}")
            elif len(match) == 2:  # (메뉴, 수량)
                menu, qty = match
                parsed_orders.append(f"{menu.strip()} {qty}")

        print(f"패턴 기반 분리: '{order_text}' → {parsed_orders}")
        return parsed_orders

    # 분리할 수 없으면 원본 반환
    return [order_text.strip()]

# 다중 주문 처리
def process_multiple_orders(session_id: str, orders: List[str]) -> str:
    successful_orders = []
    failed_orders = []

    # 각 주문을 개별 처리
    for order in orders:
        menu_text, quantity, error_type = parse_single_order(order)

        if error_type != "success":
            if error_type == "수량 없음":
                failed_orders.append(f"'{order}': 수량을 다시 말씀해주세요")
            elif error_type == "메뉴 없음":
                failed_orders.append(f"'{order}': 메뉴를 다시 말씀해주세요")
            elif error_type == "아예 인식 안됨":
                failed_orders.append(f"'{order}': 다시 말씀해주세요")
            else:
                failed_orders.append(f"'{order}': 주문을 인식할 수 없습니다")
            continue

        # 메뉴 검색
        menu = search_menu(menu_text)
        if not menu:
            failed_orders.append(f"'{order}': '{menu_text}' 메뉴를 찾을 수 없습니다.")
            continue

        # 수량 검증
        if quantity <= 0:
            failed_orders.append(f"'{order}': 수량은 1 이상이어야 합니다.")
            continue

        successful_orders.append({
            "menu_item": menu["menu_item"],
            "price": menu["price"],
            "quantity": quantity,
            "original": order
        })

    # 실패한 주문이 있으면 에러 메시지 반환
    if failed_orders:
        error_msg = "다음 주문에 문제가 있습니다:\n" + "\n".join(failed_orders)
        raise HTTPException(status_code=400, detail=error_msg)

    # 모든 주문이 성공한 경우
    if not successful_orders:
        raise HTTPException(status_code=400, detail="처리할 수 있는 주문이 없습니다.")

    # 다중 주문 세션 업데이트
    total_items = sum(order["quantity"] for order in successful_orders)

    success = redis_session_manager.update_session(
        session_id,
        "packaging",
        {
            "orders": successful_orders,
            "total_items": total_items,
            "menu_item": None,  # 명시적 제거
            "quantity": None  # 명시적 제거
        }
    )

    if not success:
        raise HTTPException(status_code=500, detail="세션 업데이트에 실패했습니다.")

    # 성공 메시지 생성
    order_summary = []
    for order in successful_orders:
        order_summary.append(f"'{order['menu_item']}' {order['quantity']}개")

    return f"다음 주문이 접수되었습니다: {', '.join(order_summary)}"

# 메뉴와 수량을 한번에 파싱하는 함수
def parse_single_order(order_text: str) -> Tuple[Optional[str], Optional[int], str]:
    config = load_quantity_config()
    units = config.get("units", ["개", "그릇", "잔", "인분", "마리", "판"])

    # 동적으로 패턴 생성
    unit_pattern = '|'.join(re.escape(unit) for unit in units)

    # 1. 수량 파싱 시도
    quantity = parse_quantity_from_text(order_text)

    if quantity is None:
        # 수량이 없는 경우 - 메뉴만 있는지 확인
        menu_text = re.sub(rf'\s*({unit_pattern})', '', order_text).strip()
        if menu_text:
            return menu_text, None, "수량 없음"
        else:
            return None, None, "아예 인식 안됨"

    # 2. 수량이 있는 경우 메뉴 추출
    menu_text = extract_menu_from_text(order_text, quantity)

    if not menu_text:
        # 수량만 있고 메뉴가 없는 경우
        return None, quantity, "메뉴 없음"

    return menu_text, quantity, "success"

# 수량을 알고 있을 때 메뉴 추출
def extract_menu_from_text(order_text: str, quantity: int) -> str:
    config = load_quantity_config()

    # 1. 찾은 숫자 패턴 제거
    text = re.sub(rf'{quantity}\s*\w*', '', order_text).strip()

    # 2. 한글 숫자도 제거 (있다면)
    korean_numbers = config.get("korean_numbers", {})

    for korean_word, value in korean_numbers.items():
        if value == quantity:
            text = text.replace(korean_word, '').strip()

    units = config.get("units", ["개", "그릇", "잔", "인분", "마리", "판", "조각", "줄", "공기", "병"])
    unit_pattern = '|'.join(re.escape(unit) for unit in units)
    text = re.sub(rf'\s*({unit_pattern})', '', text).strip()

    return text

# 포장 방식 벡터 검색
def search_packaging(packaging_text: str) -> str | None:
    try:
        query_vector = model.encode([packaging_text])[0]

        results = client.query_points(
            collection_name="packaging_options",  # 포장 옵션 컬렉션
            query=query_vector.tolist(),
            limit=3,
            score_threshold=0.2
        )

        if results.points:
            enhanced_results = []
            for result in results.points:
                packaging_name = result.payload['packaging_item']
                packaging_type = result.payload['type']
                vector_score = result.score

                # 여러 fuzzy 점수 계산
                ratio_score = fuzz.ratio(packaging_text, packaging_name) / 100
                partial_score = fuzz.partial_ratio(packaging_text, packaging_name) / 100
                token_score = fuzz.token_sort_ratio(packaging_text, packaging_name) / 100

                # 최고 fuzzy 점수 선택
                best_fuzzy = max(ratio_score, partial_score, token_score)

                # 결합 점수
                final_score = 0.7 * vector_score + 0.3 * best_fuzzy

                enhanced_results.append((packaging_type, final_score, vector_score, best_fuzzy))

            enhanced_results.sort(key=lambda x: x[1], reverse=True)

            print(f"'{packaging_text}' 포장 검색:")
            for packaging, final, vector, fuzzy in enhanced_results:
                print(f"  - {packaging}: 최종={final:.3f} (벡터={vector:.3f}, Fuzzy={fuzzy:.3f})")

            if enhanced_results[0][1] >= 0.45:  # 낮은 임계값
                return enhanced_results[0][0]  # 실제 포장 타입 반환 ("포장" 또는 "매장식사")

    except Exception as e:
        print(f"포장 검색 중 오류: {e}")

    return None

# 포장 방식 선택 처리
def process_packaging(session_id: str, packaging_type: str) -> str:
    session = redis_session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="유효하지 않은 세션입니다.")

    if session["step"] != "packaging":
        raise HTTPException(status_code=400, detail="현재 포장 선택 단계가 아닙니다.")

    # 벡터 검색으로 포장 방식 인식
    packaging = search_packaging(packaging_type)
    if not packaging:
        raise HTTPException(status_code=404, detail="포장 방식을 인식할 수 없습니다. (예: 포장, 매장식사)")

    # Redis 세션 업데이트 (완료 단계로)
    success = redis_session_manager.update_session(
        session_id,
        "packaging",
        {"packaging_type": packaging}
    )

    if not success:
        raise HTTPException(status_code=500, detail="세션 업데이트에 실패했습니다.")

    return f"{packaging}"