from fastapi import HTTPException
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer
import difflib
from fuzzywuzzy import fuzz

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

