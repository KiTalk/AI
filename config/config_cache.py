import re
from functools import lru_cache
from typing import List, Dict, Tuple, Pattern
from core.utils.config_loader import load_config

# 수량 패턴 설정 캐싱
@lru_cache(maxsize=8)
def get_quantity_config() -> Dict:
    return load_config('quantity_patterns')

# 온도 패턴 설정 캐싱
@lru_cache(maxsize=8)
def get_temperature_config() -> Dict:
    return load_config('temperature_patterns')

# 메뉴 설정 캐싱
@lru_cache(maxsize=8)
def get_menu_config() -> Dict:
    return load_config('menu_patterns')

# 구분자 정규식 패턴 캐싱
@lru_cache(maxsize=32)
def get_compiled_separators_pattern() -> Pattern:
    config = get_quantity_config()
    separators = config.get("separators", [",", "그리고", "하고", "랑", "와", "과"])
    pattern = '|'.join(re.escape(sep) for sep in separators)
    return re.compile(pattern)

# 단위 정규식 패턴 캐싱
@lru_cache(maxsize=32)
def get_compiled_unit_pattern() -> Pattern:
    config = get_quantity_config()
    units = config.get("units", ["개", "그릇", "잔", "인분", "마리", "판", "조각", "줄", "공기", "병"])
    unit_pattern = '|'.join(re.escape(unit) for unit in units)
    return re.compile(rf'\s*({unit_pattern})')

# 수량 정규식 패턴 캐싱
@lru_cache(maxsize=32)
def get_compiled_quantity_pattern() -> Pattern:
    config = get_quantity_config()
    korean_numbers = config.get("korean_numbers", {})
    korean_nums = '|'.join(re.escape(num) for num in korean_numbers.keys())
    return re.compile(rf'(\d+|{korean_nums})')

# 숫자 추출 패턴 캐싱
@lru_cache(maxsize=32)
def get_compiled_number_pattern() -> Pattern:
    return re.compile(r'\d+')

# 메뉴명 추출용 패턴 캐싱
@lru_cache(maxsize=32)
def get_compiled_menu_extraction_pattern() -> Pattern:
    return re.compile(r'\s*\w*')

# 온도 키워드 리스트 캐싱
@lru_cache(maxsize=16)
def get_temperature_keywords() -> Tuple[List[str], List[str], List[str]]:
    temp_config = get_temperature_config()
    cold_keywords = temp_config.get("cold_expressions", [])
    hot_keywords = temp_config.get("hot_expressions", [])
    all_keywords_lower = [k.lower() for k in cold_keywords + hot_keywords]
    return cold_keywords, hot_keywords, all_keywords_lower

# 한글 숫자 매핑 캐싱
@lru_cache(maxsize=16)
def get_korean_numbers() -> Dict[str, int]:
    config = get_quantity_config()
    return config.get("korean_numbers", {})

# 단위 리스트 캐싱
@lru_cache(maxsize=16)
def get_units_list() -> List[str]:
    config = get_quantity_config()
    return config.get("units", ["개", "그릇", "잔", "인분", "마리", "판", "조각", "줄", "공기", "병"])

# 구분자 리스트 캐싱
@lru_cache(maxsize=16)
def get_separators_list() -> List[str]:
    config = get_quantity_config()
    return config.get("separators", [",", "그리고", "하고", "랑", "와", "과"])

# 확인/부정 키워드 캐싱
@lru_cache(maxsize=16)
def get_confirmation_keywords() -> Tuple[List[str], List[str]]:
    positive_words = ["응", "네", "예", "맞아", "좋아", "그래", "ok", "오케이", "yes", "ㅇㅇ", "맞습니다"]
    negative_words = ["아니", "아니야", "싫어", "안돼", "노", "no", "아니오", "ㄴㄴ", "취소"]
    return positive_words, negative_words

# 포장 방식 키워드 매핑 캐싱
@lru_cache(maxsize=16)
def get_packaging_keywords() -> Dict[str, str]:
    return {
        "포장": "포장",
        "takeout": "포장",
        "매장식사": "매장식사",
        "dine_in": "매장식사"
    }

# 유사도 임계값 설정 캐싱
@lru_cache(maxsize=8)
def get_similarity_thresholds() -> Dict[str, float]:
    temp_config = get_temperature_config()
    return {
        "temperature_threshold": temp_config.get("threshold", 0.45),
        "temperature_high_confidence": temp_config.get("high_confidence_threshold", 0.7),
        "menu_similarity_threshold": 0.45,
        "popular_bonus": 0.03,
        "rapidfuzz_threshold": 85
    }

# 설정 관련 모든 캐시 정리
def clear_config_caches():
    # 설정 캐시
    get_quantity_config.cache_clear()
    get_temperature_config.cache_clear()
    get_menu_config.cache_clear()

    # 패턴 캐시
    get_compiled_separators_pattern.cache_clear()
    get_compiled_unit_pattern.cache_clear()
    get_compiled_quantity_pattern.cache_clear()
    get_compiled_number_pattern.cache_clear()
    get_compiled_menu_extraction_pattern.cache_clear()

    # 키워드 캐시
    get_temperature_keywords.cache_clear()
    get_korean_numbers.cache_clear()
    get_units_list.cache_clear()
    get_separators_list.cache_clear()
    get_confirmation_keywords.cache_clear()
    get_packaging_keywords.cache_clear()

    # 임계값 캐시
    get_similarity_thresholds.cache_clear()

# 설정 캐시 예열
def warmup_config_cache():
    # 자주 사용되는 설정들을 미리 로드
    get_quantity_config()
    get_temperature_config()
    get_compiled_separators_pattern()
    get_compiled_unit_pattern()
    get_compiled_quantity_pattern()
    get_temperature_keywords()
    get_korean_numbers()
    get_units_list()
    get_separators_list()
    get_confirmation_keywords()
    get_packaging_keywords()
    get_similarity_thresholds()

# 단위 필수 여부 확인
def is_unit_required() -> bool:
    config = get_quantity_config()
    return config.get("unit_required", False)

# 기본 온도 설정 반환
def get_default_temperature() -> str:
    config = get_temperature_config()
    return config.get("default_temperature", "hot")

def get_menu_search_limit() -> int:
    return 5

def get_vector_score_threshold() -> float:
    pass