from typing import Any, Dict, Optional
from fastapi import HTTPException
from config.naver_stt_settings import logger

from services.redis_session_service import session_manager
from services.order_at_once_service import OrderAtOnceService

class OrderRetryService:

    def __init__(self, base_service: Optional[OrderAtOnceService] = None):
        self.base = base_service or OrderAtOnceService()

    def _load_session_or_404(self, session_id: str) -> Dict[str, Any]:
        session = session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="세션이 없거나 만료되었습니다.")
        return session

    async def update_packaging_only(self, session_id: str, packaging: str) -> Dict[str, Any]:
        packaging = (packaging or "").strip()
        if packaging not in {"포장", "매장식사"}:
            raise HTTPException(status_code=400, detail="packaging은 '포장' 또는 '매장식사'만 허용됩니다.")

        session = self._load_session_or_404(session_id)
        old_data = (session.get("data") or {})
        old_order = (old_data.get("order_at_once") or {})

        new_order = {
            **old_order,
            "packaging": packaging,
        }

        if not session_manager.update_session(
            session_id=session_id,
            step="packaging_updated",
            data={
                "packaging_type": packaging,
                "order_at_once": new_order,
            },
        ):
            raise HTTPException(status_code=500, detail="Redis 세션 업데이트 실패")

        logger.info(f"[order-retry] 포장여부 업데이트: {session_id} -> {packaging}")
        return {
            "session_id": session_id,
            "packaging": packaging,
            "order_at_once": new_order,
        }

    async def update_temp_only(self, session_id: str, temp: str) -> Dict[str, Any]:
        temp = (temp or "").lower().strip()
        if temp not in {"hot", "ice"}:
            raise HTTPException(status_code=400, detail="temp는 'hot' 또는 'ice'만 허용됩니다.")

        session = self._load_session_or_404(session_id)
        old_data = (session.get("data") or {})
        old_order = (old_data.get("order_at_once") or {})

        current_name = old_data.get("menu_item") or (old_order.get("menu", {}) or {}).get("name")
        new_menu_id = self.base.resolve_menu_id(current_name, temp) if current_name else None

        new_order = {
            **old_order,
            "temp": temp,
            "menu_id": new_menu_id if new_menu_id is not None else old_order.get("menu_id"),
        }

        if not session_manager.update_session(
            session_id=session_id,
            step="temp_updated",
            data={
                "menu_id": new_menu_id if new_menu_id is not None else old_data.get(
                    "menu_id"),
                "order_at_once": new_order,
            },
        ):
            raise HTTPException(status_code=500, detail="Redis 세션 업데이트 실패")

        logger.info(f"[order-retry] 온도 업데이트: {session_id} -> {temp} (menu_id={new_menu_id})")
        return {
            "session_id": session_id,
            "temp": temp,
            "menu_id": new_menu_id,
            "order_at_once": new_order,
        }
