import os
import re
import json
import uuid
from typing import Dict, List, Any, Optional, Tuple
from fuzzywuzzy import fuzz, process
from qdrant_client import QdrantClient
from config.naver_stt_settings import logger
from services.redis_session_service import session_manager


class OrderAtOnceService:
    def __init__(self):
        qdrant_url = os.getenv("QDRANT_URL")
        api_key = os.getenv("QDRANT_API_KEY")
        if qdrant_url:
            self.client = QdrantClient(url=qdrant_url, api_key=api_key)
        else:
            host = os.getenv("QDRANT_HOST", "localhost")
            port = int(os.getenv("QDRANT_PORT", "6333"))
            self.client = QdrantClient(host=host, port=port, api_key=api_key)

        self.menu_collection = os.getenv("MENU_COLLECTION", "menu")
        self.packaging_collection = os.getenv("PACKAGING_COLLECTION", "packaging_options")

        self.fuzzy_threshold = int(os.getenv("FUZZY_THRESHOLD", "70"))
        self.packaging_threshold = float(os.getenv("PACKAGING_THRESHOLD", "0.45"))

        self.qdrant_score_threshold = float(os.getenv("QDRANT_SCORE_THRESHOLD", "0.2"))
        self.qdrant_limit = int(os.getenv("QDRANT_LIMIT", "10"))
        self.menu_min_score = float(os.getenv("MENU_MIN_SCORE", "0.45"))

        self.temp_strict = os.getenv("TEMP_STRICT", "true").lower() == "true"
        self.temp_both_values = {v.strip().lower() for v in os.getenv("TEMP_BOTH_VALUES", "both,all,any,상관없음").split(",") if v}

        self.w_vector = float(os.getenv("SIM_WEIGHT_VECTOR", "0.6"))
        self.w_fuzzy = float(os.getenv("SIM_WEIGHT_FUZZY", "0.4"))

        self._load_quantity_patterns()
        self._load_temperature_patterns_from_file()

        self._menu_cache: List[Dict[str, Any]] = []
        self._load_menu_cache()

        self._embed_model = None
        self._embedding_model_name = os.getenv("EMBEDDING_MODEL", "jhgan/ko-sroberta-multitask")

        logger.info("OrderAtOnceService 초기화 완료")

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
                self.korean_numbers = {"한": 1, "두": 2, "세": 3}
                self.default_quantity = 1
                logger.warning("quantity_patterns.json 미존재 → 기본값 사용")
        except Exception as e:
            logger.error(f"수량 패턴 로드 오류: {e}")
            self.quantity_patterns = [r"(\d+)\s*(개|잔)"]
            self.korean_numbers = {"한": 1, "두": 2, "세": 3}
            self.default_quantity = 1

    def _load_temperature_patterns_from_file(self):
        cfg_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "config",
            "temperature_patterns.json",
        )
        try:
            if os.path.exists(cfg_path):
                with open(cfg_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)

                cold_exp = cfg.get("cold_expressions") or cfg.get("ice_keywords") or []
                hot_exp = cfg.get("hot_expressions") or cfg.get("hot_keywords") or []

                self.ice_keywords: List[str] = cold_exp or ["아이스", "차가운", "시원한", "냉", "콜드", "ice", "cold", "iced"]
                self.hot_keywords: List[str] = hot_exp or ["뜨거운", "따뜻한", "핫", "온", "hot", "warm"]
                self.default_temperature: str = cfg.get("default_temperature", "hot")
                logger.info("temperature_patterns.json 로드 완료")
            else:
                self.ice_keywords = ["아이스", "차가운", "시원한", "냉", "콜드", "ice", "cold", "iced"]
                self.hot_keywords = ["뜨거운", "따뜻한", "핫", "온", "hot", "warm"]
                self.default_temperature = "hot"
                logger.warning("temperature_patterns.json 미존재 → 기본값 사용")
        except Exception as e:
            logger.error(f"온도 패턴 로드 오류: {e}")
            self.ice_keywords = ["아이스", "차가운", "시원한"]
            self.hot_keywords = ["뜨거운", "따뜻한", "핫"]
            self.default_temperature = "hot"

    def _normalize_temp(self, t: str) -> str:
        t = (t or "").lower()
        if t in {"hot", "ice", "none"}:
            return t
        if t in {"iced", "cold"}:
            return "ice"
        if t in {"warm"}:
            return "hot"
        return ""

    def _load_menu_cache(self):
        try:
            points, _ = self.client.scroll(
                collection_name=self.menu_collection,
                limit=10000,
                with_payload=True
            )
            by_name: Dict[str, Dict[str, Any]] = {}
            for point in points:
                payload = point.payload or {}
                name = payload.get("menu_item", "")
                if not name:
                    continue
                temp = self._normalize_temp(payload.get("temp", ""))
                price = payload.get("price", 0)
                popular = bool(payload.get("popular", False))
                mid = payload.get("menu_id")
                if mid is None:
                    mid = getattr(point, "id", None)

                item = by_name.setdefault(name, {
                    "name": name,
                    "price": price,
                    "popular": False,
                    "available_temps": set(),
                    "temp_to_id": {}  # <-- 핵심: temp별 menu_id 매핑
                })
                item["price"] = price
                item["popular"] = item["popular"] or popular
                if temp in {"hot", "ice", "none"}:
                    item["available_temps"].add(temp)
                    if mid is not None:
                        item["temp_to_id"][temp] = mid

            menu_data: List[Dict[str, Any]] = []
            for name, info in by_name.items():
                ats = sorted(list(info["available_temps"]))
                menu_data.append({
                    "name": name,
                    "price": info["price"],
                    "popular": info["popular"],
                    "temp": (ats[0] if ats else "none"),
                    "available_temps": ats,
                    "temp_to_id": info["temp_to_id"],
                })
            self._menu_cache = menu_data
            logger.info(f"메뉴 캐시 로드 완료(집계): {len(menu_data)}개 메뉴")
        except Exception as e:
            logger.warning(f"메뉴 캐시 로드 실패: {e}")
            self._menu_cache = []

    def resolve_menu_id(self, name: str, temp: str) -> Optional[int]:
        if not name:
            return None
        want = (temp or "").lower()

        for m in self._menu_cache:
            if m["name"] == name:
                tmap = m.get("temp_to_id", {}) or {}

                # 1) 정확히 일치하는 온도 우선
                if want in tmap:
                    return tmap[want]

                # 2) 기본 hot 우선
                if "hot" in tmap:
                    return tmap["hot"]

                # 3) hot이 없고 ice만 있으면 ice
                if "ice" in tmap:
                    return tmap["ice"]

                # 4) 디저트 등 none만 있는 경우
                if "none" in tmap:
                    return tmap["none"]

                return None
        return None

    def _get_embed_model(self):
        if self._embed_model is None:
            from sentence_transformers import SentenceTransformer
            self._embed_model = SentenceTransformer(self._embedding_model_name)
            logger.info(f"Embed model ready: {self._embedding_model_name}")
        return self._embed_model

    def _infer_packaging_via_vector(self, text: str) -> str:
        try:
            model = self._get_embed_model()
            qvec = model.encode([text])[0].tolist()

            hits = self.client.search(
                collection_name=self.packaging_collection,
                query_vector=qvec,
                limit=1,
                with_payload=True
            )
            if not hits:
                return ""
            top = hits[0]
            score = float(getattr(top, "score", 0.0) or 0.0)
            ptype = (top.payload or {}).get("type", "")

            if ptype and score >= self.packaging_threshold:
                return ptype
            return ""
        except Exception as e:
            logger.warning(f"포장 판정 실패(벡터 검색): {e}")
            return ""

    def _extract_packaging_keyword(self, text: str) -> str:
        t = (text or "").lower()
        # 포장 계열
        if any(k in t for k in
               ["포장", "테이크아웃", "takeout", "take-out", "to go", "togo"]):
            return "포장"
        # 매장 계열
        if any(k in t for k in
               ["매장", "먹고", "for here", "here", "dine-in", "dine in"]):
            return "매장식사"
        return ""

    def _detect_temperature_and_clean(self, user_text: str) -> Tuple[str, str]:
        text_lower = user_text.lower()
        if any(kw.lower() in text_lower for kw in self.ice_keywords):
            temp = "ice"
        elif any(kw.lower() in text_lower for kw in self.hot_keywords):
            temp = "hot"
        else:
            temp = getattr(self, "default_temperature", "hot")
        cleaned = self._normalize_text_for_menu(user_text)
        return cleaned, temp

    def _normalize_text_for_menu(self, s: str) -> str:
        cleaned = s
        try:
            cleaned = re.sub(r"(\d+)\s*(개|잔)", " ", cleaned)
        except re.error:
            pass
        for kw in self.ice_keywords + self.hot_keywords:
            cleaned = re.sub(re.escape(kw), " ", cleaned, flags=re.IGNORECASE)
        for kw in ["포장", "테이크아웃", "매장", "먹고", "가져가", "take out", "to go", "for here"]:
            cleaned = re.sub(re.escape(kw), " ", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'[\"\'“”‘’`]', " ", cleaned)
        cleaned = re.sub(r'[(){}\[\],.!?]', " ", cleaned)
        common_words = ["해줘", "해주세요", "주세요", "좀", "요", "하나", "으로", "을", "를", "이", "가"]
        for word in common_words:
            cleaned = re.sub(re.escape(word), " ", cleaned, flags=re.IGNORECASE)
        cleaned = " ".join(cleaned.split()).strip()
        return cleaned

    def _extract_quantity(self, text: str) -> int:
        for pattern in self.quantity_patterns:
            m = re.search(pattern, text)
            if m:
                try:
                    return int(m.group(1))
                except Exception:
                    pass
        for k, v in self.korean_numbers.items():
            if re.search(fr"{re.escape(k)}\s*(잔|개)?(만|더)?", text):
                return v
        return self.default_quantity

    def _determine_final_temp(self, user_temp: Optional[str], menu_available_temps: List[str]) -> str:
        allow = {"hot", "ice"}
        ats = [t.lower() for t in (menu_available_temps or []) if isinstance(t, str)]
        ats = [t for t in ats if t in allow]
        if not ats:
            return "hot"
        if user_temp:
            ut = user_temp.lower()
            if ut in allow and ut in ats:
                return ut
        if "ice" in ats and "hot" not in ats:
            return "ice"
        if "hot" in ats and "ice" not in ats:
            return "hot"
        return "hot"

    def _extract_user_temperature(self, text: str) -> Optional[str]:
        t = (text or "").lower()
        try:
            for kw in getattr(self, "ice_keywords", []):
                if kw.lower() in t:
                    return "ice"
            for kw in getattr(self, "hot_keywords", []):
                if kw.lower() in t:
                    return "hot"
        except Exception:
            pass
        return None

    async def _extract_menu_fuzzy(self, text: str, user_temp: Optional[str]) -> Dict[str, Any]:
        try:
            cleaned_text = self._clean_text_for_menu_search(text)
            quantity = self._extract_quantity(text)

            if not cleaned_text or not self._menu_cache:
                return {
                    "menu_id": None,
                    "name": "",
                    "quantity": quantity,
                    "similarity": 0.0,
                    "popular": "",
                    "temp": "",
                    "price": 0,
                    "method": "no_data"
                }

            menu_names = [menu["name"] for menu in self._menu_cache]
            best = process.extractOne(cleaned_text, menu_names, scorer=fuzz.ratio)

            if best and best[1] >= self.fuzzy_threshold:
                matched = None
                for m in self._menu_cache:
                    if m["name"] == best[0]:
                        matched = m
                        break
                if matched:
                    available_temps = matched.get("available_temps", [])
                    final_temp = self._determine_final_temp(user_temp, available_temps)
                    menu_id = self.resolve_menu_id(matched["name"], final_temp)
                    return {
                        "menu_id": menu_id,
                        "name": matched["name"],
                        "quantity": quantity,
                        "popular": matched.get("popular", "") if matched.get("popular") is not None else "",
                        "temp": final_temp,
                        "price": matched.get("price", 0),
                    }

            return {
                "menu_id": None,
                "name": "",
                "quantity": quantity,
                "popular": "",
                "temp": "",
                "price": 0,
                "method": "no_match"
            }
        except Exception as e:
            logger.error(f"fuzzywuzzy 메뉴 추출 오류: {e}")
            return {
                "menu_id": None,
                "name": "",
                "quantity": self.default_quantity,
                "similarity": 0.0,
                "popular": "",
                "temp": "",
                "price": 0,
                "method": "error",
                "error": str(e)
            }

    def _clean_text_for_menu_search(self, text: str) -> str:
        cleaned = text
        for pattern in self.quantity_patterns:
            try:
                cleaned = re.sub(pattern, " ", cleaned)
            except re.error:
                logger.warning(f"수량 패턴 무시(정규식 오류): {pattern}")
        for keyword in self.ice_keywords + self.hot_keywords:
            cleaned = re.sub(re.escape(keyword), " ", cleaned, flags=re.IGNORECASE)
        for kw in ["포장", "테이크아웃", "매장", "먹고", "가져가", "take out", "to go", "for here"]:
            cleaned = re.sub(re.escape(kw), " ", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'[\"\'“”‘’`]', " ", cleaned)
        cleaned = re.sub(r'[(){}\[\],.!?]', " ", cleaned)
        common_words = ["해줘", "해주세요", "주세요", "좀", "요", "하나", "으로", "을", "를", "이", "가"]
        for word in common_words:
            cleaned = re.sub(re.escape(word), " ", cleaned, flags=re.IGNORECASE)
        cleaned = " ".join(cleaned.split()).strip()
        logger.debug(f"[menu-clean] raw='{text}' -> cleaned='{cleaned}'")
        return cleaned

    async def process_order_text(self, text: str) -> Dict[str, Any]:
        try:
            session_id = session_manager.create_session()
            return await self.process_order_with_session(text, session_id)
        except Exception as e:
            logger.error(f"하위 호환성 처리 오류: {e}")
            session_id = str(uuid.uuid4())
            return {
                "menu": {
                    "menu_id": None,
                    "name": "",
                    "quantity": 1,
                    "similarity": 0.0,
                    "popular": None,
                    "temp": "",
                    "price": 0,
                    "method": "error"
                },
                "original_text": text,
                "session_id": session_id,
                "error": str(e)
            }

    async def process_order_with_session(self, text: str, session_id: str) -> Dict[str, Any]:
        try:
            user_temp = self._extract_user_temperature(text)
            menu_info = await self._extract_menu_fuzzy(text, user_temp)
            packaging = self._extract_packaging_keyword(text) or self._infer_packaging_via_vector(text)

            order_data = {
                "menu": menu_info,
                "packaging": packaging,
                "original_text": text,
                "status": "completed",
                "step": "order_at_once_completed"
            }

            session_manager.update_session(
                session_id=session_id,
                step="completed",
                data={
                    "menu_id": menu_info.get("menu_id"),
                    "menu_item": menu_info.get("name", ""),
                    "quantity": menu_info.get("quantity", 1),
                    "packaging_type": packaging or "",
                    "order_at_once": {
                        **order_data,
                        "menu_id": menu_info.get("menu_id"),
                    },
                }
            )

            result = {
                "menu": menu_info,
                "packaging": packaging,
                "original_text": text,
                "session_id": session_id
            }
            logger.info(f"한번에 주문 처리 완료: {session_id} - {menu_info.get('name', '')} ({menu_info.get('menu_id')})")
            return result

        except Exception as e:
            logger.error(f"한번에 주문 처리 오류: {e}")
            error_menu = {
                "menu_id": None,
                "name": "",
                "quantity": 1,
                "similarity": 0.0,
                "popular": "",
                "temp": "",
                "price": 0,
                "method": "error"
            }
            try:
                session_manager.update_session(
                    session_id=session_id,
                    step="error",
                    data={
                        "menu_id": None,
                        "menu_item": "",
                        "quantity": 1,
                        "packaging_type": "",
                        "order_at_once": {
                            "menu_id": None,
                            "price": 0,
                            "popular": "",
                            "temp": "",
                            "similarity": 0.0,
                            "method": "error",
                            "original_text": text,
                            "error": str(e)
                        }
                    }
                )
            except:
                pass

            return {
                "menu": error_menu,
                "packaging": "",
                "original_text": text,
                "session_id": session_id,
                "error": str(e)
            }

    async def get_order_by_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        try:
            session = session_manager.get_session(session_id)
            if session and "order_at_once" in session.get("data", {}):
                return session["data"]["order_at_once"]
            return None
        except Exception as e:
            logger.error(f"세션 조회 오류: {e}")
            return None
