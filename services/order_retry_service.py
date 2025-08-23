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

    async def update_temp_only(self, session_id: str, temp: str) -> Dict[
        str, Any]:
        temp = (temp or "").lower().strip()
        if temp not in {"hot", "ice"}:
            raise HTTPException(status_code=400,
                                detail="temp는 'hot' 또는 'ice'만 허용됩니다.")

        session = self._load_session_or_404(session_id)

        old_data = (session.get("data") or {})
        old_order = (old_data.get("order_at_once") or {})
        logger.info(f"[DEBUG] 업데이트 전 old_data: {old_data}")
        logger.info(f"[DEBUG] 업데이트 전 old_order: {old_order}")

        current_name = old_data.get("menu_item") or (
                old_order.get("menu", {}) or {}).get("name")
        new_menu_id = self.base.resolve_menu_id(current_name,
                                                temp) if current_name else None
        logger.info(
            f"[DEBUG] current_name: {current_name}, new_menu_id: {new_menu_id}")

        new_order = {
            **old_order,
            "temp": temp,
            "menu_id": new_menu_id if new_menu_id is not None else old_order.get(
                "menu_id"),
        }

        if "menu" in new_order and isinstance(new_order["menu"], dict):
            new_order["menu"] = {
                **new_order["menu"],
                "temp": temp,
                "menu_id": new_menu_id if new_menu_id is not None else
                new_order["menu"].get("menu_id"),
            }
        logger.info(f"[DEBUG] new_order: {new_order}")

        update_data = {
            "menu_id": new_menu_id if new_menu_id is not None else old_data.get(
                "menu_id"),
            "temp": temp,
            "order_at_once": new_order,
        }
        logger.info(f"[DEBUG] 업데이트할 데이터: {update_data}")

        update_result = session_manager.update_session(
            session_id=session_id,
            step="temp_updated",
            data=update_data,
        )
        logger.info(f"[DEBUG] Redis 업데이트 결과: {update_result}")

        if not update_result:
            raise HTTPException(status_code=500, detail="Redis 세션 업데이트 실패")

        updated_session = session_manager.get_session(session_id)
        logger.info(f"[DEBUG] 업데이트 후 전체 세션: {updated_session}")

        logger.info(
            f"[order-retry] 온도 업데이트: {session_id} -> {temp} (menu_id={new_menu_id})")
        return {
            "session_id": session_id,
            "temp": temp,
            "menu_id": new_menu_id,
            "order_at_once": new_order,
        }