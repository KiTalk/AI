from fastapi import HTTPException
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer
import difflib
from fuzzywuzzy import fuzz
import json
import os
import re
from typing import Union

# Qdrant 클라이언트 초기화
client = QdrantClient(url="http://localhost:6333")

# SentenceTransformer 모델 초기화
model = SentenceTransformer('jhgan/ko-sroberta-multitask')

def search_menu(menu_item: str) -> str | None:
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
                vector_score = result.score

                # 여러 fuzzy 점수 계산
                ratio_score = fuzz.ratio(menu_item, menu_name) / 100
                partial_score = fuzz.partial_ratio(menu_item, menu_name) / 100
                token_score = fuzz.token_sort_ratio(menu_item, menu_name) / 100

                # 최고 fuzzy 점수 선택
                best_fuzzy = max(ratio_score, partial_score, token_score)

                # 결합 점수
                final_score = 0.7 * vector_score + 0.3 * best_fuzzy

                enhanced_results.append((menu_name, final_score, vector_score, best_fuzzy))

            enhanced_results.sort(key=lambda x: x[1], reverse=True)

            print(f"'{menu_item}' 실용적 검색:")
            for menu, final, vector, fuzzy in enhanced_results:
                print(f"  - {menu}: 최종={final:.3f} (벡터={vector:.3f}, Fuzzy={fuzzy:.3f})")

            if enhanced_results[0][1] >= 0.45:  # 낮은 임계값
                return enhanced_results[0][0]

    except Exception as e:
        print(f"검색 중 오류: {e}")

    return None

def process_menu(menu_item: str) -> str:
    found = search_menu(menu_item)
    if not found:
        raise HTTPException(status_code=404, detail="메뉴를 찾을 수 없습니다.")
    return f"'{found}' 메뉴가 선택되었습니다."

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
def parse_quantity_from_text(text: str) -> int:
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

    raise ValueError("수량을 인식할 수 없습니다")

def process_quantity(quantity_input: Union[int, str]) -> str:
    try:
        if isinstance(quantity_input, str):
            # 자연어 텍스트인 경우 파싱 (ValueError 발생 가능)
            quantity = parse_quantity_from_text(quantity_input)
            print(f"수량 파싱: '{quantity_input}' → {quantity}")
        else:
            # 기존 int 타입 처리
            quantity = quantity_input

        # 기존 검증 로직 유지
        if quantity <= 0:
            raise HTTPException(status_code=400, detail="수량은 1 이상이어야 합니다.")

        return f"{quantity}"

    except ValueError:
        raise HTTPException(status_code=400, detail="수량을 정확히 말씀해주세요. (예: 2개, 한잔, 다섯개)")
