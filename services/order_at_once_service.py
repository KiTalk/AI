import os
import re
import json
from typing import Dict, List, Any, Optional
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

        self.menu_collection = "menu"
        self.packaging_collection = "packaging_options"
        self.fuzzy_threshold = int(os.getenv("FUZZY_THRESHOLD", "70"))
        self.packaging_threshold = float(os.getenv("PACKAGING_THRESHOLD", "0.6"))

        self._load_config_files()
        self._menu_cache = None
        self._load_menu_cache()
        self._embed_model = None
        self._pack_keywords = None
        self._load_packaging_keywords()

        logger.info("OrderAtOnceService 초기화 완료")

    def _load_config_files(self):
        self.quantity_patterns = self._get_config("quantity_patterns.json", "regex_patterns", [r"(\d+)\s*(개|잔)"])
        self.korean_numbers = self._get_config("quantity_patterns.json", "korean_numbers", {"한": 1, "두": 2, "세": 3})
        self.default_quantity = self._get_config("quantity_patterns.json", "default_quantity", 1)
        self.ice_keywords = self._get_config("temperature_patterns.json", "ice_keywords", ["아이스", "차가운", "시원한"])
        self.hot_keywords = self._get_config("temperature_patterns.json", "hot_keywords", ["뜨거운", "따뜻한", "핫"])

    def _get_config(self, filename: str, key: str, default_value):
        try:
            cfg_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", filename)
            if os.path.exists(cfg_path):
                with open(cfg_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                return cfg.get(key, default_value)
            else:
                logger.warning(f"{filename} 미존재 → 기본값 사용")
                return default_value
        except Exception as e:
            logger.error(f"{filename} 로드 오류: {e}")
            return default_value

    def _get_embed_model(self):
        if self._embed_model is None:
            from sentence_transformers import SentenceTransformer
            self._embed_model = SentenceTransformer("jhgan/ko-sroberta-multitask")
        return self._embed_model

    def _normalize_temp(self, t: str) -> str:
        t = (t or "").lower()
        if t in {"hot", "ice"}:
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
                item = by_name.setdefault(name, {
                    "name": name,
                    "price": price,
                    "popular": False,
                    "available_temps": set()
                })
                item["price"] = price
                item["popular"] = item["popular"] or popular
                if temp in {"hot", "ice"}:
                    item["available_temps"].add(temp)

            menu_data = []
            for name, info in by_name.items():
                ats = sorted(list(info["available_temps"]))
                menu_data.append({
                    "name": name,
                    "price": info["price"],
                    "popular": info["popular"],
                    "temp": (ats[0] if ats else "none"),
                    "available_temps": ats
                })

            self._menu_cache = menu_data
            logger.info(f"메뉴 캐시 로드 완료(집계): {len(menu_data)}개 메뉴")
        except Exception as e:
            logger.warning(f"메뉴 캐시 로드 실패: {e}")
            self._menu_cache = []

    def _load_packaging_keywords(self):
        try:
            pts, _ = self.client.scroll(
                collection_name=self.packaging_collection,
                limit=10000,
                with_payload=True
            )
            pack = []
            dine = []
            for p in pts:
                payload = p.payload or {}
                ptype = (payload.get("type") or "").lower()
                alias = (payload.get("alias") or "").lower()
                if not ptype or not alias:
                    continue
                pat = re.sub(r"\s+", r"\\s*", re.escape(alias))
                if ptype in {"포장", "takeout"}:
                    pack.append(re.compile(pat))
                elif ptype in {"매장", "매장식사", "dine-in"}:
                    dine.append(re.compile(pat))
            self._pack_keywords = {"포장": pack, "매장식사": dine}
            logger.info(f"포장 키워드 로드: 포장={len(pack)}, 매장식사={len(dine)}")
        except Exception as e:
            logger.warning(f"포장 키워드 로드 실패: {e}")
            self._pack_keywords = {"포장": [], "매장식사": []}

    def _normalize_packaging(self, s: str) -> str:
        s = (s or "").lower()
        if s in {"포장", "takeout", "take-out", "to-go", "togo", "테이크아웃"}:
            return "포장"
        if s in {"매장", "매장식사", "dine-in", "dinein", "here"}:
            return "매장식사"
        return ""

    def _extract_packaging(self, text: str) -> str:
        try:
            t = (text or "").lower()

            hits = []
            if self._pack_keywords:
                for m in self._pack_keywords.get("포장", []):
                    for x in m.finditer(t):
                        hits.append((x.start(), "포장"))
                for m in self._pack_keywords.get("매장식사", []):
                    for x in m.finditer(t):
                        hits.append((x.start(), "매장식사"))
            if hits:
                hits.sort(key=lambda x: x[0])
                return hits[-1][1]

            model = self._get_embed_model()
            vec = model.encode([text])[0].tolist()
            res = self.client.search(
                collection_name=self.packaging_collection,
                query_vector=vec,
                limit=3,
                with_payload=True
            )
            if res:
                best = max(res, key=lambda r: float(r.score or 0.0))
                score = float(best.score or 0.0)
                raw_type = (best.payload or {}).get("type", "")
                norm = self._normalize_packaging(raw_type)
                if score >= max(0.45, self.packaging_threshold) and norm:
                    logger.info(f"포장여부(Vector): {norm} (score={score:.3f})")
                    return norm

            return ""
        except Exception as e:
            logger.warning(f"포장여부 추출 오류: {e}")
            return ""

    async def process_order_with_session(self, text: str, session_id: str) -> Dict[str, Any]:
        try:
            user_temp = self._extract_user_temperature(text)
            menu_info = await self._extract_menu_fuzzy(text, user_temp)
            packaging = self._extract_packaging(text)

            session_manager.update_session(
                session_id=session_id,
                step="completed",
                data={
                    "menu_item": menu_info.get("name", ""),
                    "quantity": menu_info.get("quantity", 1),
                    "packaging_type": packaging,
                    "order_at_once": {
                        "price": menu_info.get("price", 0),
                        "popular": menu_info.get("popular", ""),
                        "temp": menu_info.get("temp", ""),
                        "similarity": menu_info.get("similarity", 0.0),
                        "method": menu_info.get("method", ""),
                        "original_text": text
                    }
                }
            )

            result = {
                "menu": menu_info,
                "packaging": packaging,
                "original_text": text,
                "session_id": session_id
            }

            logger.info(f"한번에 주문 처리 완료: {session_id} - {menu_info.get('name', '')} - {packaging}")
            return result

        except Exception as e:
            logger.error(f"한번에 주문 처리 오류: {e}")
            error_menu = {
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
                        "menu_item": "",
                        "quantity": 1,
                        "packaging_type": "",
                        "order_at_once": {
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

    def _extract_user_temperature(self, text: str) -> Optional[str]:
        text_lower = text.lower()
        for keyword in self.ice_keywords:
            if keyword.lower() in text_lower:
                return "ice"
        for keyword in self.hot_keywords:
            if keyword.lower() in text_lower:
                return "hot"
        return None

    def _determine_final_temp(self, user_temp: Optional[str], menu_available_temps: List[str]) -> str:
        allow = {"hot", "ice"}
        ats = [t.lower() for t in (menu_available_temps or []) if isinstance(t, str)]
        ats = [t for t in ats if t in allow]

        if not ats:
            return "hot"  # 온도 무의미(디저트) 등

        if user_temp:
            ut = user_temp.lower()
            if ut in allow and ut in ats:
                return ut

        if "ice" in ats and "hot" not in ats:
            return "ice"
        if "hot" in ats and "ice" not in ats:
            return "hot"
        return "hot"

    async def _extract_menu_fuzzy(self, text: str, user_temp: Optional[str]) -> Dict[str, Any]:
        try:
            cleaned_text = self._clean_text_for_menu_search(text)
            quantity = self._extract_quantity(text)

            if not cleaned_text or not self._menu_cache:
                return {
                    "name": "",
                    "quantity": quantity,
                    "similarity": 0.0,
                    "popular": "",
                    "temp": "",
                    "price": 0,
                    "method": "no_data"
                }

            menu_names = [menu["name"] for menu in self._menu_cache]
            best_match = process.extractOne(cleaned_text, menu_names, scorer=fuzz.ratio)

            if best_match and best_match[1] >= self.fuzzy_threshold:
                matched_menu = None
                for menu in self._menu_cache:
                    if menu["name"] == best_match[0]:
                        matched_menu = menu
                        break

                if matched_menu:
                    available_temps = matched_menu.get("available_temps", [])
                    final_temp = self._determine_final_temp(user_temp, available_temps)
                    return {
                        "name": matched_menu["name"],
                        "quantity": quantity,
                        "similarity": best_match[1] / 100.0,
                        "popular": matched_menu["popular"] if matched_menu["popular"] is not None else "",
                        "temp": final_temp,
                        "price": matched_menu["price"],
                        "method": "fuzzywuzzy"
                    }

            return {
                "name": "",
                "quantity": quantity,
                "similarity": 0.0,
                "popular": "",
                "temp": "",
                "price": 0,
                "method": "no_match"
            }

        except Exception as e:
            logger.error(f"fuzzywuzzy 메뉴 추출 오류: {e}")
            return {
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
        for keyword in ["포장", "테이크아웃", "매장", "먹고", "가져가"]:
            cleaned = re.sub(re.escape(keyword), " ", cleaned, flags=re.IGNORECASE)
        polite_patterns = [
            r'(?:(?<=\s)|^)좀(?=\s|$)',
            r'조금',
            r'부탁(?:해|드립니다|드려요)?',
            r'해주(?:세|십)?요',
            r'해주세요',
            r'해줘',
            r'주(?:시겠|실)어요\??',
            r'주세요'
        ]
        for p in polite_patterns:
            cleaned = re.sub(p, " ", cleaned, flags=re.IGNORECASE)

        josa_pattern = r'(?<=[가-힣])(?:을|를|은|는|이|가|에|에서|으로|로|과|와|요)(?=\s|$)'
        cleaned = re.sub(josa_pattern, " ", cleaned)
        cleaned = " ".join(cleaned.split()).strip()
        logger.debug(f"[menu-clean] raw='{text}' -> cleaned='{cleaned}'")
        return cleaned
