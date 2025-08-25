import redis
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import logging
import os

logger = logging.getLogger(__name__)

# Redis 기반 세션 관리 클래스
class RedisSessionManager:
    VALID_STEPS = ["started", "packaging", "phone_choice", "phone_input", "completed", "fully_completed"]

    # 세션 단계 유효성 검사
    def is_valid_step(self, step: str) -> bool:
        return step in self.VALID_STEPS

    # Redis 연결 초기화
    def __init__(self, redis_url: str = None):
        host = os.getenv("REDIS_HOST", "localhost")
        self.redis_url = redis_url or f"redis://{host}:6379/0"

        try:
            self.redis_client = redis.from_url(redis_url, decode_responses=True)
            self.redis_client.ping()
            logger.info(f"Redis 연결 성공: {redis_url}")
        except redis.RedisError as e:
            logger.error(f"Redis 연결 실패: {e}")
            raise

    # 새 세션 생성
    def create_session(self, expire_minutes: int = 30) -> str:
        session_id = str(uuid.uuid4())
        session_data = {
            "created_at": datetime.now().isoformat(),
            "expires_at": (datetime.now() + timedelta(minutes=expire_minutes)).isoformat(),
            "step": "started",
            "data": {
                "menu_item": None,
                "quantity": None,
                "packaging_type": None
            }
        }

        try:
            # 30분
            self.redis_client.setex(
                f"session:{session_id}",
                expire_minutes * 60,
                json.dumps(session_data)
            )
            logger.info(f"세션 생성 완료: {session_id}")
            return session_id
        except redis.RedisError as e:
            logger.error(f"세션 생성 실패: {e}")
            raise

    # 세션 조회
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        try:
            session_json = self.redis_client.get(f"session:{session_id}")
            if not session_json:
                logger.warning(f"세션 없음 또는 만료: {session_id}")
                return None

            session_data = json.loads(session_json)
            logger.debug(f"세션 조회 성공: {session_id}")
            return session_data
        except (redis.RedisError, json.JSONDecodeError) as e:
            logger.error(f"세션 조회 실패: {e}")
            return None

    # 세션 업데이트
    def update_session(self, session_id: str, step: str, data: Dict[str, Any], expire_minutes: int = 30) -> bool:
        try:
            session = self.get_session(session_id)
            if not session:
                logger.warning(f"업데이트할 세션 없음: {session_id}")
                return False

            session["step"] = step
            session["data"].update(data)
            session["updated_at"] = datetime.now().isoformat()

            # Redis에 다시 저장 (TTL 연장)
            self.redis_client.setex(
                f"session:{session_id}",
                expire_minutes * 60,
                json.dumps(session)
            )
            logger.info(f"세션 업데이트 완료: {session_id}, step: {step}")
            return True
        except redis.RedisError as e:
            logger.error(f"세션 업데이트 실패: {e}")
            return False

    # 세션 삭제
    def delete_session(self, session_id: str) -> bool:
        try:
            result = self.redis_client.delete(f"session:{session_id}")
            if result:
                logger.info(f"세션 삭제 완료: {session_id}")
                return True
            else:
                logger.warning(f"삭제할 세션 없음: {session_id}")
                return False
        except redis.RedisError as e:
            logger.error(f"세션 삭제 실패: {e}")
            return False

    # 세션 만료 시간 연장
    def extend_session(self, session_id: str, expire_minutes: int = 30) -> bool:
        try:
            result = self.redis_client.expire(f"session:{session_id}", expire_minutes * 60)
            if result:
                logger.info(f"세션 만료시간 연장: {session_id} (+{expire_minutes}분)")
                return True
            else:
                logger.warning(f"연장할 세션 없음: {session_id}")
                return False
        except redis.RedisError as e:
            logger.error(f"세션 연장 실패: {e}")
            return False

    # 모든 세션 조회
    def get_all_sessions(self) -> Dict[str, Dict[str, Any]]:
        try:
            session_keys = self.redis_client.keys("session:*")
            sessions = {}

            for key in session_keys:
                session_id = key.replace("session:", "")
                session_data = self.get_session(session_id)
                if session_data:
                    sessions[session_id] = session_data

            logger.info(f"전체 세션 조회: {len(sessions)}개")
            return sessions
        except redis.RedisError as e:
            logger.error(f"전체 세션 조회 실패: {e}")
            return {}

    # 만료된 세션 정리
    def cleanup_expired_sessions(self) -> int:
        try:
            # 수동 정리가 필요한 경우를 위해 구현
            session_keys = self.redis_client.keys("session:*")
            expired_count = 0

            for key in session_keys:
                ttl = self.redis_client.ttl(key)
                if ttl == -2:  # 키가 존재하지 않음
                    expired_count += 1

            logger.info(f"만료된 세션 정리 완료: {expired_count}개")
            return expired_count
        except redis.RedisError as e:
            logger.error(f"세션 정리 실패: {e}")
            return 0

    # 세션 통계 정보
    def get_session_stats(self) -> Dict[str, Any]:
        try:
            total_sessions = len(self.redis_client.keys("session:*"))

            # 단계별 세션 수 계산
            step_counts = {}
            sessions = self.get_all_sessions()

            for session_data in sessions.values():
                step = session_data.get("step", "unknown")
                step_counts[step] = step_counts.get(step, 0) + 1

            stats = {
                "total_sessions": total_sessions,
                "step_distribution": step_counts,
                "redis_info": {
                    "connected": self.redis_client.ping(),
                    "memory_usage": self.redis_client.info("memory")["used_memory_human"]
                }
            }

            logger.info(f"세션 통계: {stats}")
            return stats
        except redis.RedisError as e:
            logger.error(f"세션 통계 조회 실패: {e}")
            return {"error": str(e)}

# 전역 Redis 세션 매니저 인스턴스
redis_session_manager = RedisSessionManager()

# 기존 코드와의 호환성을 위한 별칭
session_manager = redis_session_manager