from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer
import re
import logging
from core.utils.config_loader import load_config
from typing import Tuple, List, Dict, Any
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
from .logic_order_utils import (
    validate_session,
    validate_and_create_order_item,
    validate_order_list,
    update_session_orders,
    format_order_list,
    create_order_response,
    calculate_similarity_score
)

# 로거 설정
logger = logging.getLogger(__name__)

# Qdrant 클라이언트 초기화
client = QdrantClient(url="http://localhost:6333")

# SentenceTransformer 모델 초기화
model = SentenceTransformer('jhgan/ko-sroberta-multitask')

# quantity_patterns 설정을 로드
def load_quantity_config():
    return load_config('quantity_patterns')

# 메뉴 찾기
def search_menu(menu_item: str) -> Dict[str, Any]:
    try:
        # 온도 감지 및 메뉴명 추출
        cleaned_menu, temperature = detect_temperature(menu_item)

        query_vector = model.encode([cleaned_menu])[0]

        results = client.query_points(
            collection_name="menu",
            query=query_vector.tolist(),
            limit=10,
            score_threshold=0.2
        )

        # 메뉴 찾지 못했을 때
        if not results.points:
            raise MenuNotFoundException(menu_item)

        enhanced_results = []
        for result in results.points:
            menu_name = result.payload['menu_item']
            price = result.payload['price']
            popular = result.payload.get('popular', False)
            db_temp = result.payload.get('temp', 'hot')
            vector_score = result.score

            # 수정: 온도 매칭 확인 로직 추가
            if db_temp != temperature:
                continue

            final_score, vector_score, best_fuzzy = calculate_similarity_score(cleaned_menu, menu_name)

            enhanced_results.append((menu_name, price, popular, db_temp, final_score, vector_score, best_fuzzy))

        # 수정: 온도 필터링 후 결과가 없으면 예외 처리 추가
        if not enhanced_results:
            raise MenuNotFoundException(menu_item)

        enhanced_results.sort(key=lambda x: x[4], reverse=True)

        logger.info(f"'{menu_item}' 검색 (온도: {temperature}):")

        for menu, price, popular, temp, final, vector, fuzzy in enhanced_results:
            logger.info(f"  - {menu}[{temp.upper()}]({price}원): 최종={final:.3f}")

        if enhanced_results[0][4] >= 0.45:
            return {
                "menu_item": enhanced_results[0][0],
                "price": enhanced_results[0][1],
                "popular": enhanced_results[0][2],
                "temp": enhanced_results[0][3]
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
        _ = validate_session(session_id, "started")

        # 주문 분리
        individual_orders = split_multiple_orders(order_text)
        print(f"주문 분리: {individual_orders}")

        processed_orders = process_multiple_orders(session_id, individual_orders)

        updated_session = validate_session(session_id)
        orders = updated_session["data"]["orders"]

        message = f"다음 주문이 접수되었습니다: {format_order_list(orders)}"
        if hasattr(processed_orders, 'failed_orders') and processed_orders.failed_orders:
            message += f"\n참고: 다음 주문은 인식하지 못했습니다: {', '.join(processed_orders.failed_orders)}"

        return create_order_response(message, orders)

    except (MenuNotFoundException, OrderParsingException,
            SessionUpdateFailedException, InvalidSessionStepException, SessionNotFoundException):
        raise
    except Exception as e:
        logger.error(f"주문 처리 중 예상치 못한 오류: {e}")
        raise OrderParsingException("주문 처리 중 오류가 발생했습니다")

# 개별 주문으로 분리
def split_multiple_orders(order_text: str) -> List[str]:
    config = load_quantity_config()

    # 0단계: 온도 키워드 보호
    temp_config = load_config('temperature_patterns')
    temp_keywords = temp_config.get("cold_expressions", []) + temp_config.get("hot_expressions", [])

    # 온도 키워드를 벡터 유사도로 보호
    protected_text = order_text
    words = order_text.split()
    replacements = {}

    for i, word in enumerate(words):
        best_match = None
        highest_score = 0.0

        for keyword in temp_keywords:
            final_score, _, _ = calculate_similarity_score(word.lower(), keyword)
            if final_score > highest_score and final_score > 0.6:  # 임계값
                highest_score = final_score
                best_match = keyword

        if best_match:
            placeholder = f"__TEMP_{i}__"
            protected_text = protected_text.replace(word, placeholder)
            replacements[placeholder] = word
            logger.info(f"🔒 온도 키워드 보호: '{word}' (유사: '{best_match}', 점수: {highest_score:.3f}) → '{placeholder}'")

    logger.info(f"🔒 보호된 텍스트: '{order_text}' → '{protected_text}'")

    # 1단계: config의 구분자로 분리 시도 (대비로 뒤에 예시 추가함)
    separators = config.get("separators", [",", "그리고", "하고", "랑", "와", "과"])
    pattern = '|'.join(re.escape(sep) for sep in separators)
    orders = re.split(pattern, protected_text)
    orders = [order.strip() for order in orders if order.strip()]

    # 구분자로 분리되었으면 반환
    if len(orders) > 1:
        # 플레이스홀더를 원래 키워드로 복원
        restored_orders = []
        for order in orders:
            restored_order = order
            for placeholder, original in replacements.items():
                restored_order = restored_order.replace(placeholder, original)
            restored_orders.append(restored_order)
        return restored_orders

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
        full_pattern = rf'([가-힣\s__TEMP_\d+__]*?[가-힣]+[가-힣\s__TEMP_\d+__]*?)\s*{quantity_pattern}\s*({unit_pattern})?'
    else:
        # 단위 선택적
        full_pattern = rf'([가-힣\s__TEMP_\d+__]*?[가-힣]+[가-힣\s__TEMP_\d+__]*?)\s*{quantity_pattern}\s*({unit_pattern})?'

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

        restored_orders = []
        for order in parsed_orders:
            restored_order = order
            for placeholder, original in replacements.items():
                restored_order = restored_order.replace(placeholder, original)
            restored_orders.append(restored_order)


        logger.info(f"패턴 기반 분리: '{order_text}' → {parsed_orders}")
        return parsed_orders

    # 분리할 수 없으면 원본 반환
    return [order_text.strip()]

# 다중 주문 처리
def process_multiple_orders(session_id: str, orders: List[str]) -> None:
    _ = validate_session(session_id)

    successful_orders = []
    failed_orders = []

    try:
        for order in orders:
            try:
                menu_text, quantity = parse_single_order_simplified(order)
                validated_order = validate_and_create_order_item(menu_text, quantity, search_menu)
                successful_orders.append(validated_order)
            except MenuNotFoundException:
                failed_orders.append(f"'{order}': 메뉴를 찾을 수 없습니다")
            except Exception as e:
                # 기타 예외도 관대하게 처리
                logger.warning(f"주문 '{order}' 처리 중 오류: {e}")
                failed_orders.append(f"'{order}': 처리할 수 없습니다")

        validate_order_list(successful_orders)

        success = update_session_orders(session_id, successful_orders, "packaging")

        if not success:
            raise SessionUpdateFailedException(session_id, "포장 정보 업데이트")

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
        "original": order,
        "popular": menu["popular"],
        "temp": menu["temp"]
    }

def search_packaging(packaging_text: str) -> str:
    if packaging_text in ["포장하기", "takeout"]:
        return "포장하기"
    elif packaging_text in ["먹고가기", "dine_in"]:
        return "먹고가기"
    else:
        raise PackagingNotFoundException(packaging_text)

def process_packaging(session_id: str, packaging_type: str) -> str:
    _ = validate_session(session_id, "packaging")

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

# 확인 응답 분석 (긍정/부정 판단)
def analyze_confirmation(text: str) -> bool:
    text = text.strip().lower()

    positive_words = ["응", "네", "예", "맞아", "좋아", "그래", "ok", "오케이", "yes", "ㅇㅇ", "맞습니다"]
    negative_words = ["아니", "아니야", "싫어", "안돼", "노", "no", "아니오", "ㄴㄴ", "취소"]

    # 부정 먼저 체크 (더 명확한 거부 의사)
    for word in negative_words:
        if word in text:
            return False

    # 긍정 체크
    for word in positive_words:
        if word in text:
            return True

    # 기본값은 True (긍정으로 처리)
    return True

# 벡터 + fuzzy 조합 온도 감지 (search_menu와 동일한 방식)
def detect_temperature(text: str) -> Tuple[str, str]:
    # config 로드
    temp_config = load_config('temperature_patterns')
    cold_expressions = temp_config.get("cold_expressions", [])
    hot_expressions = temp_config.get("hot_expressions", [])
    threshold = temp_config.get("threshold", 0.45)
    default_temp = temp_config.get("default_temperature", "hot")

    # 1단계: 단어 분리
    words = text.strip().split()
    all_expressions = cold_expressions + hot_expressions

    # 2단계: 각 단어를 온도 키워드와 비교
    best_temp = default_temp
    best_keyword = ""
    best_word = ""
    highest_score = 0.0

    for word in words:
        word_lower = word.lower()
        for keyword in all_expressions:
            final_score, _, _ = calculate_similarity_score(word_lower, keyword)

            if final_score > highest_score and final_score > threshold:
                highest_score = final_score
                best_keyword = keyword
                best_word = word
                best_temp = "ice" if keyword in cold_expressions else "hot"

    # 3단계: 감지된 단어 제거
    # 3단계: 감지된 단어 제거
    cleaned_text = text
    high_confidence_threshold = temp_config.get("high_confidence_threshold", 0.7)
    if best_word and highest_score > high_confidence_threshold:
        cleaned_text = text.replace(best_word, "").strip()

    return cleaned_text, best_temp