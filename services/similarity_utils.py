from __future__ import annotations
from functools import lru_cache
from typing import Callable, Tuple, Iterable
import numpy as np
from sentence_transformers import SentenceTransformer

# 외부에서 주입할 SentenceTransformer 인스턴스 getter
_MODEL_GETTER: Callable[[], "SentenceTransformer"] | None = None

def set_model_getter(getter: Callable[[], "SentenceTransformer"]) -> None:
    global _MODEL_GETTER
    _MODEL_GETTER = getter

def _get_model():
    if _MODEL_GETTER is None:
        raise RuntimeError("SentenceTransformer 모델이 설정되지 않았습니다. set_model_getter()를 먼저 호출하세요.")
    return _MODEL_GETTER()

# 텍스트 -> 임베딩 (소문자 변환 후) 캐시. tuple로 저장해 lru_cache 키로 사용.
@lru_cache(maxsize=4096)
def encode_cached(text: str) -> Tuple[float, ...]:
    model = _get_model()
    vec = model.encode([text.lower()], show_progress_bar=False, convert_to_numpy=True)[0]
    return tuple(vec.tolist())

# 두 벡터(tuple)의 코사인 유사도.
def cosine_from_vecs(a: Tuple[float, ...], b: Tuple[float, ...]) -> float:
    a_np = np.asarray(a, dtype=np.float32)
    b_np = np.asarray(b, dtype=np.float32)

    norm_a = float(np.linalg.norm(a_np))  # float로 변환
    norm_b = float(np.linalg.norm(b_np))  # float로 변환

    if norm_a == 0 or norm_b == 0:
        return 0.0

    dot_product = float(np.dot(a_np, b_np))  # float로 변환
    denominator = norm_a * norm_b

    return dot_product / denominator

#  결합 점수(final), 벡터 점수, fuzzy 최고 점수를 반환.
def combined_score_from_vecs(
    input_vec: Tuple[float, ...],
    target_vec: Tuple[float, ...],
    input_text: str,
    target_text: str,
    vector_weight: float = 0.7,
) -> tuple[float, float, float]:
    vector_score = cosine_from_vecs(input_vec, target_vec)

    from rapidfuzz import fuzz as rf
    inp = input_text.lower()
    ratio = rf.ratio(target_text, inp) / 100
    partial = rf.partial_ratio(target_text, inp) / 100
    token = rf.token_sort_ratio(target_text, inp) / 100
    best_fuzzy = max(ratio, partial, token)

    final = vector_weight * vector_score + (1 - vector_weight) * best_fuzzy
    return final, vector_score, best_fuzzy

# 텍스트 두 개를 받아 캐시 임베딩 후 결합 점수를 계산.
def combined_score_from_texts(
    input_text: str,
    target_text: str,
    vector_weight: float = 0.7,
) -> tuple[float, float, float]:
    iv = encode_cached(input_text)
    tv = encode_cached(target_text)
    return combined_score_from_vecs(iv, tv, input_text, target_text, vector_weight=vector_weight)

def warmup_embeddings(texts: Iterable[str]) -> None:
    texts = [t.lower() for t in texts]
    for t in texts:
        encode_cached(t)

# 임베딩 캐시 초기화
def clear_embedding_cache() -> None:
    encode_cached.cache_clear()
