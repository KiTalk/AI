from qdrant_client import QdrantClient
from services.similarity_utils import encode_cached, warmup_embeddings
from rapidfuzz import process as rf_process, fuzz as rf_fuzz
import re
import logging
import inspect
from functools import lru_cache
from typing import Tuple, List, Dict, Any, Optional
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
# 설정 캐시 매니저 import
from config.config_cache import (
    get_compiled_separators_pattern,
    get_compiled_unit_pattern,
    get_compiled_number_pattern,
    get_temperature_keywords,
    get_korean_numbers,
    get_units_list,
    get_confirmation_keywords,
    get_packaging_keywords,
    get_similarity_thresholds,
    is_unit_required,
    get_default_temperature,
    get_menu_search_limit,
    get_vector_score_threshold
)

# 로거 설정
logger = logging.getLogger(__name__)

# Qdrant 클라이언트 싱글톤
_client: Optional[QdrantClient] = None

def get_qdrant_client() -> QdrantClient:
    global _client
    if _client is None:
        _client = QdrantClient(url="http://localhost:6333")
    return _client

try:
    from qdrant_client.http.models import Filter, FieldCondition, MatchValue
except ImportError:
    from qdrant_client.models import Filter, FieldCondition, MatchValue

# 메뉴 찾기
def search_menu(menu_item: str) -> Dict[str, Any]:
    try:
        # 온도 감지 및 메뉴명 추출
        cleaned_menu, user_temp, temp_detected = detect_temperature(menu_item)

        query_vector = list(encode_cached(cleaned_menu))
        client = get_qdrant_client()

        # Qdrant 클라이언트 API 버전 호환성 체크
        sig = inspect.signature(client.query_points)
        filter_kw = "filter" if "filter" in sig.parameters else (
            "query_filter" if "query_filter" in sig.parameters else None
        )

        try:
            from qdrant_client.http.models import Filter, FieldCondition, MatchValue
        except ImportError:
            from qdrant_client.models import Filter, FieldCondition, MatchValue

        # 2) 공통 쿼리 함수 (temp 필터는 옵션)
        def run_query(temp_filter: str | None):
            flt = None
            if temp_filter is not None:
                flt = Filter(must=[FieldCondition(key="temp", match=MatchValue(value=temp_filter))])

            # 동적으로 결정된 filter_kw 사용
            kwargs = {
                "collection_name": "menu",
                "query": query_vector,
                "limit": get_menu_search_limit(),
                "score_threshold": get_vector_score_threshold(),
                "with_payload": True,
                "with_vectors": False,
            }
            
            if flt is not None and filter_kw is not None:
                kwargs[filter_kw] = flt # type: ignore
            
            return client.query_points(**kwargs)

        # 3) 온도 우선순위: 사용자지정 > DB온도 > 기본값
        # 사용자가 온도를 명시했다면 해당 온도로만 검색, 아니면 모든 온도로 검색
        if temp_detected:
            # 사용자가 온도를 명시한 경우: 해당 온도로만 검색
            tried = [user_temp]
        else:
            # 사용자가 온도를 명시하지 않은 경우: 모든 온도로 검색 (DB 온도 우선)
            tried = [None]  # 필터 없이 모든 메뉴 검색
        
        enhanced_results = None

        for temp_try in tried:
            results = run_query(temp_try)
            if not results or not getattr(results, "points", None):
                continue

            enhanced = _process_menu_results(results, cleaned_menu)
            if enhanced:
                enhanced_results = enhanced
                break

        if not enhanced_results:
            raise MenuNotFoundException(menu_item)

        top = enhanced_results[0]

        thresholds = get_similarity_thresholds()

        if top[4] >= thresholds["menu_similarity_threshold"]:
            # 온도 우선순위 적용: 사용자지정 > DB온도 > 기본값
            final_temp = user_temp if temp_detected else top[3]  # DB온도 사용
            
            return {
                "menu_item": top[0],
                "price": top[1],
                "popular": top[2],
                "temp": final_temp,
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

# 메뉴 검색 결과 처리
def _process_menu_results(results, cleaned_menu: str) -> List[Tuple]:
    logger.info(f"🔍 Qdrant 응답 타입: {type(results)}")
    logger.info(f"🔍 Qdrant 응답 내용: {results}")

    thresholds = get_similarity_thresholds()
    pop_bonus = thresholds["popular_bonus"]
    enhanced_results = []

    # 배치로 메뉴명 추출
    menu_names = []
    valid_results = []

    for p in results.points:  # ← 여기만 수정!
        payload = p.payload or {}
        menu_name = payload.get("menu_item")
        price = payload.get("price")
        if menu_name and price is not None:
            menu_names.append(menu_name)
            valid_results.append((menu_name, price, payload.get('popular', False), payload.get('temp', 'hot')))

    # 배치 임베딩 예열
    if menu_names:
        warmup_embeddings([cleaned_menu] + menu_names)

    # 유사도 계산
    for menu_name, price, popular, db_temp in valid_results:
        final_score, vector_score, best_fuzzy = calculate_similarity_score(cleaned_menu, menu_name)
        if popular:
            final_score += pop_bonus
        enhanced_results.append((menu_name, price, popular, db_temp, final_score, vector_score, best_fuzzy))

    enhanced_results.sort(key=lambda x: x[4], reverse=True)

    # 로깅 (상위 3개만)
    logger.info(f"'{cleaned_menu}' 검색 결과:")
    for menu, price, popular, temp, final, _, _ in enhanced_results[:3]:
        logger.info(f"  - {menu}[{temp.upper()}]({price}원): 최종={final:.3f}")

    return enhanced_results

# 자연어 수량 파싱 함수
@lru_cache(maxsize=128)
def parse_quantity_from_text(text: str) -> int:
    text = text.strip().lower()

    # 1. 아라비아 숫자 추출
    number_pattern = get_compiled_number_pattern()
    match = number_pattern.search(text)

    if match:
        return int(match.group())

    # 2. config 파일의 한글 숫자 확인
    korean_numbers = get_korean_numbers()

    for korean_word, value in korean_numbers.items():
        if korean_word in text:
            return value

    return 0

# 메뉴와 수량을 함께 처리하는 함수
def process_order(session_id: str, order_text: str) -> Dict[str, Any]:
    try:
        _ = validate_session(session_id, "started")

        # 주문 분리
        individual_orders = split_multiple_orders(order_text)
        logger.info("주문 분리: %s", individual_orders)

        process_multiple_orders(session_id, individual_orders)

        updated_session = validate_session(session_id)
        orders = updated_session["data"]["orders"]

        message = f"다음 주문이 접수되었습니다: {format_order_list(orders)}"

        return create_order_response(message, orders)

    except (MenuNotFoundException, OrderParsingException,
            SessionUpdateFailedException, InvalidSessionStepException, SessionNotFoundException):
        raise
    except Exception as e:
        logger.error(f"주문 처리 중 예상치 못한 오류: {e}")
        raise OrderParsingException("주문 처리 중 오류가 발생했습니다")

# 온도 키워드 복원
def _restore_temperature_keywords(orders: List[str], replacements: Dict[str, str]) -> List[str]:
    restored_orders = []
    for order in orders:
        restored_order = order
        for placeholder, original in replacements.items():
            restored_order = restored_order.replace(placeholder, original)
        restored_orders.append(restored_order)
    return restored_orders

# 개별 주문으로 분리
def split_multiple_orders(order_text: str) -> List[str]:
    cold_expressions, hot_expressions, temp_keywords_lower = get_temperature_keywords()

    # 온도 키워드를 벡터 유사도로 보호
    protected_text = order_text
    words = order_text.split()
    replacements = {}

    thresholds = get_similarity_thresholds()
    rapidfuzz_threshold = thresholds["rapidfuzz_threshold"]

    for i, word in enumerate(words):
        cand = rf_process.extractOne(word.lower(), temp_keywords_lower, scorer=rf_fuzz.ratio)  # type: ignore
        if cand and cand[1] >= rapidfuzz_threshold:  # 임계치(0~100)
            placeholder = f"__TEMP_{i}__"
            protected_text = protected_text.replace(word, placeholder)
            replacements[placeholder] = word


    # 1단계: config의 구분자로 분리 시도 (대비로 뒤에 예시 추가함)
    separator_pattern = get_compiled_separators_pattern()
    orders = separator_pattern.split(protected_text)
    orders = [order.strip() for order in orders if order.strip()]

    # 구분자로 분리되었으면 반환
    if len(orders) > 1:
        return _restore_temperature_keywords(orders, replacements)

    # 2단계: 패턴 기반 자동 분리 (config 기반)
    units = get_units_list()
    korean_numbers = get_korean_numbers()

    # 동적으로 패턴 생성
    unit_pattern = '|'.join(re.escape(unit) for unit in units)
    korean_nums = '|'.join(re.escape(num) for num in korean_numbers.keys())
    quantity_pattern = rf'(\d+|{korean_nums})'

    # 전체 패턴: 메뉴명 + 수량 + 단위(선택)
    # 단위가 없어도 동작하도록 수정
    if is_unit_required():
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

        restored_orders = _restore_temperature_keywords(parsed_orders, replacements)

        logger.info(f"패턴 기반 분리: '{order_text}' → {parsed_orders}")
        return restored_orders

    # 분리할 수 없으면 원본 반환
    return [order_text.strip()]

# 다중 주문 처리
def process_multiple_orders(session_id: str, orders: List[str]) -> None:
    _ = validate_session(session_id)

    successful_orders = []
    failed_orders = []

    menu_texts = []
    order_data = []

    try:
        for order in orders:
            try:
                menu_text, quantity = parse_single_order_simplified(order)
                menu_texts.append(menu_text)
                order_data.append((order, menu_text, quantity))
            except Exception as e:
                # 기타 예외도 관대하게 처리
                logger.warning(f"주문 '{order}' 처리 중 오류: {e}")
                failed_orders.append(f"'{order}': 처리할 수 없습니다")

        if menu_texts:
            warmup_embeddings(menu_texts)

        # 개별 주문 처리
        for order, menu_text, quantity in order_data:
            try:
                validated_order = validate_and_create_order_item(menu_text, quantity, search_menu)

                # 중복 체크 후 추가 또는 합치기
                existing = None
                for existing_order in successful_orders:
                    if existing_order["menu_item"] == validated_order["menu_item"] and existing_order["temp"] == \
                            validated_order["temp"]:
                        existing = existing_order
                        break

                if existing:
                    existing["quantity"] += validated_order["quantity"]
                    existing["original"] += f", {validated_order['original']}"  # 원본 주문 합치기
                else:
                    successful_orders.append(validated_order)

            except MenuNotFoundException:
                failed_orders.append(f"'{order}': 메뉴를 찾을 수 없습니다")
            except Exception as e:
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

    # 1. 찾은 숫자 패턴 제거
    text = re.sub(rf'{quantity}\s*\w*', '', order_text).strip()

    # 2. 한글 숫자도 제거 (있다면)
    korean_numbers = get_korean_numbers()

    for korean_word, value in korean_numbers.items():
        if value == quantity:
            text = text.replace(korean_word, '').strip()
            break

    unit_pattern = get_compiled_unit_pattern()
    text = unit_pattern.sub('', text).strip()

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

@lru_cache(maxsize=16)
def search_packaging(packaging_text: str) -> str:
    packaging_keywords = get_packaging_keywords()
    if packaging_text in packaging_keywords:
        return packaging_keywords[packaging_text]
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
@lru_cache(maxsize=64)
def analyze_confirmation(text: str) -> bool:
    text = text.strip().lower()

    positive_words, negative_words = get_confirmation_keywords()

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
@lru_cache(maxsize=256)
def detect_temperature(text: str) -> Tuple[str, str, bool]:
    logger.info(f"🔍 온도감지 입력: '{text}'")

    cold_expressions, hot_expressions, _ = get_temperature_keywords()
    thresholds = get_similarity_thresholds()

    # config 로드
    threshold = thresholds["temperature_threshold"]
    high_confidence_threshold = thresholds["temperature_high_confidence"]
    default_temp = get_default_temperature()

    # 1단계: 단어 분리
    text_lower = text.lower()
    all_expressions = cold_expressions + hot_expressions

    # 2단계: 각 단어를 온도 키워드와 비교
    best_temp = default_temp
    best_word = ""
    highest_score = 0.0
    temp_detected = False

    for word in all_expressions:
        if word in text_lower:
            final_score = 1.0  # 포함되면 100% 매칭으로 처리

            if final_score > highest_score and final_score > threshold:
                highest_score = final_score
                best_word = word
                best_temp = "ice" if word in cold_expressions else "hot"
                temp_detected = True

    # 3단계: 감지된 단어 제거
    cleaned_text = text
    if best_word and highest_score > high_confidence_threshold:
        cleaned_text = text_lower.replace(best_word, "").strip()

    logger.info(f"🔍 감지결과 - 온도: {best_temp}, 제거단어: '{best_word}', 정리된텍스트: '{cleaned_text}', 감지됨: {temp_detected}")

    return cleaned_text, best_temp, temp_detected