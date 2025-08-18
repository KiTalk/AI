from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer
from fuzzywuzzy import fuzz
import json
import os
import re
import logging
from typing import Tuple, List, Optional, Dict, Any
from .redis_session_service import redis_session_manager
from core.exceptions.logic_exceptions import (
    MenuNotFoundException,
    OrderParsingException,
    PackagingNotFoundException,
)
from core.exceptions.session_exceptions import (
    SessionNotFoundException,
    InvalidSessionStepException,
    SessionUpdateFailedException
)

# 로거 설정
logger = logging.getLogger(__name__)

# Qdrant 클라이언트 초기화
client = QdrantClient(url="http://localhost:6333")

# SentenceTransformer 모델 초기화
model = SentenceTransformer('jhgan/ko-sroberta-multitask')

# 설정 캐시
_config_cache = None

# config 로딩
def load_quantity_config():
    global _config_cache

    if _config_cache is not None:
        return _config_cache

    try:
        config_dir = os.path.join(os.path.dirname(__file__), '..', 'config')
        config_file = os.path.join(config_dir, 'quantity_patterns.json')

        with open(config_file, 'r', encoding='utf-8') as f:
            _config_cache = json.load(f)
            return _config_cache

    except FileNotFoundError:
        logger.error(f"설정 파일을 찾을 수 없습니다: {config_file}")
        raise OrderParsingException("시스템 설정 오류가 발생했습니다")

    except json.JSONDecodeError as e:
        logger.error(f"설정 파일 JSON 파싱 오류: {e}")
        raise OrderParsingException("시스템 설정 오류가 발생했습니다")

    except Exception as e:
        logger.error(f"설정 파일 로드 실패: {e}")
        raise OrderParsingException("시스템 설정 오류가 발생했습니다")

# 메뉴 찾기
def search_menu(menu_item: str) -> Dict[str, Any]:
    try:
        query_vector = model.encode([menu_item])[0]

        results = client.query_points(
            collection_name="menu",
            query=query_vector.tolist(),
            limit=3,
            score_threshold=0.2
        )

        # 메뉴 찾지 못했을 때
        if not results.points:
            raise MenuNotFoundException(menu_item)

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

        logger.info(f"'{menu_item}' 실용적 검색:")

        for menu, price, final, vector, fuzzy in enhanced_results:
            logger.info(f"  - {menu}({price}원): 최종={final:.3f}")

        if enhanced_results[0][2] >= 0.45:
            return {
                "menu_item": enhanced_results[0][0],
                "price": enhanced_results[0][1]
            }
        else:
            raise MenuNotFoundException(menu_item)

    except MenuNotFoundException:
        raise

    except ConnectionError as e:
        logger.error(f"벡터 DB 연결 실패: {e}")
        raise MenuNotFoundException(f"{menu_item} (검색 서비스 오류)")

    except Exception as e:
        logger.error(f"메뉴 검색 중 예상치 못한 오류: {e}")
        raise MenuNotFoundException(f"{menu_item} (검색 오류)")

# 자연어 수량 파싱 함수
def parse_quantity_from_text(text: str) -> int:
    text = text.strip().lower()
    config = load_quantity_config()

    # 1. 아라비아 숫자 추출
    number_match = re.search(r'\d+', text)
    if number_match:
        return int(number_match.group())

    # 2. config 파일의 한글 숫자 확인
    korean_numbers = config.get("korean_numbers", {})

    for korean_word in korean_numbers:
        if korean_word in text:
            return korean_numbers[korean_word]

    return 0

# 메뉴와 수량을 함께 처리하는 함수
def process_order(session_id: str, order_text: str) -> Dict[str, Any]:
    try:
        session = redis_session_manager.get_session(session_id)
        if not session:
            raise SessionNotFoundException(session_id)

        # started 단계에서만 실행 가능
        if session["step"] != "started":
            raise InvalidSessionStepException(session["step"], "started")

        # 주문 분리
        individual_orders = split_multiple_orders(order_text)
        print(f"주문 분리: {individual_orders}")

        message = process_multiple_orders(session_id, individual_orders)

        updated_session = redis_session_manager.get_session(session_id)
        if not updated_session:
            raise SessionUpdateFailedException(session_id, "세션 조회")

        orders = updated_session["data"]["orders"]
        total_items = updated_session["data"]["total_items"]
        total_price = sum(order["price"] * order["quantity"] for order in orders)

        return {
            "message": message,
            "orders": orders,
            "total_items": total_items,
            "total_price": total_price
        }

    except (MenuNotFoundException, OrderParsingException,
            SessionUpdateFailedException, InvalidSessionStepException, SessionNotFoundException):
        raise
    except Exception as e:
        logger.error(f"주문 처리 중 예상치 못한 오류: {e}")
        raise OrderParsingException("주문 처리 중 오류가 발생했습니다")

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

        logger.info(f"패턴 기반 분리: '{order_text}' → {parsed_orders}")
        return parsed_orders

    # 분리할 수 없으면 원본 반환
    return [order_text.strip()]

# 다중 주문 처리
def process_multiple_orders(session_id: str, orders: List[str]) -> str:
    # 원본 세션 백업
    original_session = redis_session_manager.get_session(session_id)
    if not original_session:
        raise SessionNotFoundException(session_id)

    successful_orders = []
    failed_orders = []

    try:
        for order in orders:
            try:
                validated_order = validate_single_order_simplified(order)
                successful_orders.append(validated_order)
            except MenuNotFoundException:
                failed_orders.append(f"'{order}': 메뉴를 찾을 수 없습니다")
            except Exception as e:
                # 기타 예외도 관대하게 처리
                logger.warning(f"주문 '{order}' 처리 중 오류: {e}")
                failed_orders.append(f"'{order}': 처리할 수 없습니다")

        # 하나라도 성공하면 진행 (기존에는 모든 주문이 성공해야 했음)
        if not successful_orders:
            raise OrderParsingException("인식할 수 있는 메뉴가 없습니다")

        # 세션 업데이트
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
            raise SessionUpdateFailedException(session_id, "포장 정보 업데이트")

        # 메시지 생성 (수량 0 처리 포함)
        order_summary = []
        for order in successful_orders:
            if order["quantity"] == 0:
                order_summary.append(f"'{order['menu_item']}' (수량 미지정)")
            else:
                order_summary.append(f"'{order['menu_item']}' {order['quantity']}개")

        message = f"다음 주문이 접수되었습니다: {', '.join(order_summary)}"

        # 실패한 주문이 있어도 성공한 것들은 진행하고 안내만 추가
        if failed_orders:
            message += f"\n참고: 다음 주문은 인식하지 못했습니다: {', '.join(failed_orders)}"

        return message

    except Exception as e:
        logger.error(f"다중 주문 처리 실패: {e}")
        raise

# 텍스트 파싱 ex) 짜장면 2개 -> (짜장면, 2개)
def parse_single_order_simplified(order_text: str) -> Tuple[str, int]:

    # 1. 수량 파싱 (실패시 0)
    quantity = parse_quantity_from_text(order_text)

    # 2. 메뉴 추출 (수량 제거 후)
    menu_text = extract_menu_from_text(order_text, quantity)

    # 메뉴가 없으면 예외 발생
    if not menu_text:
        raise OrderParsingException(f"메뉴명을 인식할 수 없습니다: '{order_text}'. 다시 말씀해주세요.")

    return menu_text, quantity

# 텍스트에서 메뉴 추출
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

# 전체 주문 검증
def validate_single_order_simplified(order: str) -> Dict[str, Any]:
    if not order or not isinstance(order, str):
        raise OrderParsingException("주문 텍스트가 올바르지 않습니다")

    # 메뉴와 수량 파싱
    menu_text, quantity = parse_single_order_simplified(order)

    # 메뉴 검색
    menu = search_menu(menu_text)

    # 수량이 0이어도 허용, 음수는 0으로 보정
    if quantity < 0:
        quantity = 0

    return {
        "menu_item": menu["menu_item"],
        "price": menu["price"],
        "quantity": quantity,
        "original": order
    }

def search_packaging(packaging_text: str) -> str:
    if packaging_text in ["포장하기", "takeout"]:
        return "포장하기"
    elif packaging_text in ["먹고가기", "dine_in"]:
        return "먹고가기"
    else:
        raise PackagingNotFoundException(packaging_text)

def process_packaging(session_id: str, packaging_type: str) -> str:
    session = redis_session_manager.get_session(session_id)
    if not session:
        raise SessionNotFoundException(session_id)

    if session["step"] != "packaging":
        raise InvalidSessionStepException(session["step"], "packaging")

    # 벡터 검색으로 포장 방식 인식 (이미 예외 발생하도록 수정됨)
    packaging = search_packaging(packaging_type)

    # Redis 세션 업데이트
    success = redis_session_manager.update_session(
        session_id,
        "packaging",
        {"packaging_type": packaging}
    )

    if not success:
        raise SessionUpdateFailedException(session_id, "포장 정보 업데이트")

    return f"{packaging}"