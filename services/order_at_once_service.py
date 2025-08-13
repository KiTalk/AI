import os
import re
import json
from typing import Dict, List, Any

from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams
from qdrant_client.http.exceptions import UnexpectedResponse
from config.naver_stt_settings import logger


class OrderAtOnceService:
    """
    텍스트 → (메뉴, 수량, 포장여부) 추출 서비스
    - 수량: config/quantity_patterns.json
    - 포장 키워드: config/packaging_keywords.json (없으면 안전한 기본값)
    - 메뉴/포장 벡터검색: Qdrant ('menu', 'packaging_options')
    """

    def __init__(self):
        # Qdrant 연결
        qdrant_url = os.getenv("QDRANT_URL")
        api_key = os.getenv("QDRANT_API_KEY")
        if qdrant_url:
            self.client = QdrantClient(url=qdrant_url, api_key=api_key)
        else:
            host = os.getenv("QDRANT_HOST", "localhost")
            port = int(os.getenv("QDRANT_PORT", "6333"))
            self.client = QdrantClient(host=host, port=port, api_key=api_key)

        self.menu_collection = "menu"
        self.packaging_collection = "packaging_options"

        # 임계값 (필요시 .env에서 조정)
        self.menu_sim_threshold = float(os.getenv("MENU_SIM_THRESHOLD", "0.55"))
        self.packaging_sim_threshold = float(os.getenv("PACKAGING_SIM_THRESHOLD", "0.60"))  # 살짝 낮춤

        # 설정 로드
        self._load_quantity_patterns()
        self._load_packaging_keywords()

        # SBERT 모델(지연 로딩)
        self._emb_model = None

        logger.info("OrderAtOnceService 초기화 완료 (키워드+벡터검색 하이브리드)")

    # ----------------------- 설정 로드 -----------------------

    def _load_quantity_patterns(self):
        cfg_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "config",
            "quantity_patterns.json",
        )
        try:
            if os.path.exists(cfg_path):
                with open(cfg_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                self.quantity_patterns: List[str] = cfg.get("regex_patterns", [])
                self.korean_numbers: Dict[str, int] = cfg.get("korean_numbers", {})
                self.default_quantity: int = cfg.get("default_quantity", 1)
            else:
                self.quantity_patterns = [r"(\d+)\s*(개|잔)"]
                self.korean_numbers = {}
                self.default_quantity = 1
                logger.warning("quantity_patterns.json 미존재 → 최소 기본값 사용")
        except Exception as e:
            logger.error(f"수량 패턴 로드 오류: {e}")
            self.quantity_patterns = [r"(\d+)\s*(개|잔)"]
            self.korean_numbers = {}
            self.default_quantity = 1

    def _load_packaging_keywords(self):
        """포장/매장 키워드를 config에서 로드 (없으면 기본 세트)"""
        cfg_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "config",
            "packaging_keywords.json",
        )
        try:
            if os.path.exists(cfg_path):
                with open(cfg_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                self.pack_kw_takeout: List[str] = cfg.get("takeout", [])
                self.pack_kw_dinein: List[str] = cfg.get("dine_in", [])
            else:
                # 안전한 기본값
                self.pack_kw_takeout = ["포장", "테이크아웃", "to go", "take out", "가져가", "포장으로", "포장해서"]
                self.pack_kw_dinein = ["매장", "여기서", "먹고", "마실", "먹고갈", "취식"]
                logger.warning("packaging_keywords.json 미존재 → 기본 키워드 사용")
        except Exception as e:
            logger.error(f"포장 키워드 로드 오류: {e}")
            self.pack_kw_takeout = ["포장", "테이크아웃", "to go", "take out", "가져가", "포장으로", "포장해서"]
            self.pack_kw_dinein = ["매장", "여기서", "먹고", "마실", "먹고갈", "취식"]

    # ----------------------- 유틸 -----------------------

    def _get_model(self):
        if self._emb_model is None:
            from sentence_transformers import SentenceTransformer
            self._emb_model = SentenceTransformer("jhgan/ko-sroberta-multitask")
        return self._emb_model

    # ----------------------- 퍼블릭 API -----------------------

    async def process_order_text(self, text: str) -> Dict[str, Any]:
        try:
            quantity = self._extract_quantity(text)
            packaging = await self._extract_packaging(text)
            menu_info = await self._extract_menu(text, packaging_type=packaging["type"])

            return {
                "menu": menu_info,
                "quantity": quantity,
                "packaging": packaging,
                "original_text": text,
            }

        except Exception as e:
            logger.error(f"process_order_text 오류: {e}")
            return {
                "menu": {"name": "", "similarity": 0.0, "candidates": [], "method": "error"},
                "quantity": self.default_quantity,
                "packaging": {"type": "매장식사", "similarity": 0.0, "method": "default"},
                "original_text": text,
                "error": str(e),
            }

    # ----------------------- 세부 추출 -----------------------

    def _extract_quantity(self, text: str) -> int:
        # 1) 정규식
        for pattern in self.quantity_patterns:
            m = re.search(pattern, text)
            if m:
                try:
                    return int(m.group(1))
                except Exception:
                    pass
        # 2) 한글 수사
        for k, v in self.korean_numbers.items():
            if re.search(fr"{re.escape(k)}\s*(잔|개)?(만|더)?", text):
                return v
        # 3) 기본
        return self.default_quantity

    async def _extract_packaging(self, text: str) -> Dict[str, Any]:
        low = text.lower()

        # A) 키워드 우선 (환경/설정 기반)
        for kw in self.pack_kw_takeout:
            if kw.lower() in low:
                return {"type": "포장", "similarity": 1.0, "method": "keyword"}

        for kw in self.pack_kw_dinein:
            if kw.lower() in low:
                return {"type": "매장식사", "similarity": 1.0, "method": "keyword"}

        # B) 벡터검색 (미탐지 시)
        try:
            model = self._get_model()
            vec = model.encode([text])[0].tolist()
            search = self.client.search(
                collection_name=self.packaging_collection,
                query_vector=vec,
                limit=1,
            )
            if search:
                sp = search[0]
                ptype = (sp.payload or {}).get("type", "매장식사")
                score = float(sp.score or 0.0)
                if score >= self.packaging_sim_threshold:
                    return {"type": ptype, "similarity": score, "method": "vector"}
        except Exception as e:
            logger.warning(f"포장여부 벡터검색 실패: {e}")

        # C) 기본값
        return {"type": "매장식사", "similarity": 0.0, "method": "default"}

    async def _extract_menu(self, text: str, packaging_type: str) -> Dict[str, Any]:
        """
        메뉴 검색 전 텍스트 정리:
        - 수량 패턴 제거
        - 포장 키워드 제거 (응답 일관성; setup 키워드 사용)
        """
        query = self._clean_text_for_menu_search(text)

        # 벡터검색
        try:
            model = self._get_model()
            vec = model.encode([query])[0].tolist()
            search = self.client.search(
                collection_name=self.menu_collection,
                query_vector=vec,
                limit=5,
            )
            candidates: List[Dict[str, Any]] = []
            for sp in search:
                payload = sp.payload or {}
                name = payload.get("menu_item", "") or payload.get("name", "")
                score = float(sp.score or 0.0)
                candidates.append({"name": name, "similarity": score})

            candidates.sort(key=lambda x: x["similarity"], reverse=True)
            if candidates and candidates[0]["similarity"] >= self.menu_sim_threshold:
                best = candidates[0]
                return {
                    "name": best["name"],
                    "similarity": best["similarity"],
                    "candidates": candidates,
                    "method": "vector_search",
                }

            # 확신 낮음
            return {"name": query, "similarity": 0.0, "candidates": [], "method": "no_match"}

        except Exception as e:
            logger.error(f"메뉴 벡터검색 오류: {e}")
            return {"name": query, "similarity": 0.0, "candidates": [], "method": "error", "error": str(e)}

    def _clean_text_for_menu_search(self, text: str) -> str:
        cleaned = text

        # 1) 수량 패턴 제거
        for pattern in self.quantity_patterns:
            try:
                cleaned = re.sub(pattern, " ", cleaned)
            except re.error:
                logger.warning(f"수량 패턴 무시(정규식 오류): {pattern}")

        # 2) 포장 키워드 제거 (설정 파일 기반, 중복 하드코딩 방지)
        def remove_keywords(s: str, kws: List[str]) -> str:
            for kw in kws:
                if not kw:
                    continue
                # 단순 포함 제거 (한국어 짧은 키워드 특성 고려)
                s = re.sub(re.escape(kw), " ", s, flags=re.IGNORECASE)
            return s

        cleaned = remove_keywords(cleaned, self.pack_kw_takeout)
        cleaned = remove_keywords(cleaned, self.pack_kw_dinein)

        # 공백 정리
        return " ".join(cleaned.split()).strip()

    # ----------------------- (선택) 컬렉션 초기화 -----------------------
    async def initialize_collections(self):
        """개발 편의용. 운영은 setup 스크립트 사용 권장."""
        try:
            for cname in (self.menu_collection, self.packaging_collection):
                try:
                    self.client.create_collection(
                        collection_name=cname,
                        vectors_config=VectorParams(size=768, distance=Distance.COSINE),
                    )
                    logger.info(f"컬렉션 생성: {cname}")
                except UnexpectedResponse as e:
                    if "already exists" in str(e):
                        logger.info(f"컬렉션 이미 존재: {cname}")
                    else:
                        raise
        except Exception as e:
            logger.error(f"컬렉션 초기화 오류: {e}")
            raise
