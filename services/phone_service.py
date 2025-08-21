import logging
import re
from typing import Dict, Any, Optional
from datetime import datetime
from .redis_session_service import redis_session_manager
from .logic_order_utils import (
    validate_session,
    calculate_totals
)
from database.simple_db import simple_menu_db
from core.exceptions.logic_exceptions import OrderParsingException
from core.exceptions.session_exceptions import (
    SessionNotFoundException,
    InvalidSessionStepException,
    SessionUpdateFailedException
)

logger = logging.getLogger(__name__)

# 전화번호 입력 여부 선택 처리
def process_phone_choice(session_id: str, wants_phone: bool) -> Dict[str, Any]:
    try:
        # packaging 단계에서만 접근 가능
        _ = validate_session(session_id, "packaging")

        if wants_phone:
            # 전화번호 입력하겠다고 선택
            success = redis_session_manager.update_session(
                session_id,
                "phone_choice",
                {"wants_phone": True}
            )

            if not success:
                raise SessionUpdateFailedException(session_id, "전화번호 선택 업데이트")

            return {
                "message": "전화번호를 입력해주세요.",
                "next_step": "전화번호 입력"
            }
        else:
            # 전화번호 입력 안하겠다고 선택 → 바로 완료
            return complete_order(session_id)

    except (SessionNotFoundException, InvalidSessionStepException, SessionUpdateFailedException):
        raise
    except Exception as e:
        logger.error(f"전화번호 선택 처리 중 오류: {e}")
        raise OrderParsingException("전화번호 선택 처리 중 오류가 발생했습니다")

# 전화번호 입력 처리
def process_phone_input(session_id: str, phone_number: str) -> Dict[str, Any]:
    try:
        # phone_choice 단계에서만 접근 가능
        _ = validate_session(session_id, "phone_choice")

        # 전화번호 유효성 검사
        if not is_valid_phone_number(phone_number):
            raise OrderParsingException("유효하지 않은 전화번호 형식입니다. (예: 010-1234-5678)")

        # 전화번호 정규화 (하이픈 추가)
        normalized_phone = normalize_phone_number(phone_number)

        # 세션에 전화번호 저장
        success = redis_session_manager.update_session(
            session_id,
            "phone_input",
            {"phone_number": normalized_phone}
        )

        if not success:
            raise SessionUpdateFailedException(session_id, "전화번호 저장")

        # 바로 주문 완료 처리
        return complete_order(session_id)

    except (SessionNotFoundException, InvalidSessionStepException, SessionUpdateFailedException):
        raise
    except Exception as e:
        logger.error(f"전화번호 입력 처리 중 오류: {e}")
        raise OrderParsingException("전화번호 입력 처리 중 오류가 발생했습니다")

# 주문 완료 처리 및 MYSQL 저장
def complete_order(session_id: str) -> Dict[str, Any]:
    try:
        # packaging, phone_choice 또는 phone_input 단계에서 접근 가능
        session = validate_session(session_id)

        if session["step"] not in ["packaging", "phone_choice", "phone_input"]:
            raise InvalidSessionStepException(session["step"], "packaging, phone_choice or phone_input")

        # 세션 데이터 가져오기
        orders = session["data"]["orders"]
        packaging_type = session["data"]["packaging_type"]
        phone_number = session["data"].get("phone_number")  # 없을 수도 있음

        if not orders:
            raise OrderParsingException("주문할 메뉴가 없습니다.")

        # MySQL에 주문 저장
        order_id = save_order_to_mysql(orders, packaging_type, phone_number)

        # 세션 완료로 변경 (5분간 유지)
        success = redis_session_manager.update_session(
            session_id,
            "completed",
            {
                "order_id": order_id,
                "saved_at": datetime.now().isoformat()
            },
            expire_minutes=5  # 5분만 유지
        )

        if not success:
            raise SessionUpdateFailedException(session_id, "주문 완료 처리")

        total_items, total_price = calculate_totals(orders)

        logger.info(f"주문 완료: order_id={order_id}, session_id={session_id}, 5분 후 자동 삭제")

        return {
            "message": "주문이 완료되었습니다!",
            "order_id": order_id,
            "orders": orders,
            "total_items": total_items,
            "total_price": total_price,
            "packaging": packaging_type,
            "phone_number": phone_number,
            "next_step": "주문 완료"
        }

    except (SessionNotFoundException, InvalidSessionStepException, SessionUpdateFailedException):
        raise
    except Exception as e:
        logger.error(f"주문 완료 처리 중 오류: {e}")
        raise OrderParsingException("주문 완료 처리 중 오류가 발생했습니다")

# 전화번호 유효성 검사
def is_valid_phone_number(phone_number: str) -> bool:
    # 공백과 하이픈 제거
    clean_phone = phone_number.replace('-', '').replace(' ', '')

    # 010으로 시작하고 11자리 숫자인지 확인
    pattern = r'^010\d{8}$'
    return bool(re.match(pattern, clean_phone))

# 전화번허 정규화 (010-0000-0000)
def normalize_phone_number(phone_number: str) -> str:
    clean_phone = phone_number.replace('-', '').replace(' ', '')

    if len(clean_phone) == 11 and clean_phone.startswith('010'):
        return f"{clean_phone[:3]}-{clean_phone[3:7]}-{clean_phone[7:]}"

    return phone_number  # 변환 실패시 원본 반환

# MYSQL에 주문 저장
def save_order_to_mysql(orders: list, packaging_type: str, phone_number: Optional[str] = None) -> int:
    try:
        # 총 금액 계산
        total_price = sum(order["price"] * order["quantity"] for order in orders)

        # orders 테이블에 저장
        connection = simple_menu_db.get_connection()
        if not connection:
            raise Exception("MySQL 연결 실패")

        try:
            with connection.cursor() as cursor:
                # 1. orders 테이블에 메인 주문 정보 저장
                order_sql = """
                            INSERT INTO orders (phone_number, total_price, packaging_type, created_at, status)
                            VALUES (%s, %s, %s, %s, %s) \
                            """
                cursor.execute(order_sql, (
                    phone_number,
                    total_price,
                    packaging_type,
                    datetime.now(),
                    'completed'
                ))

                # 방금 생성된 order_id 가져오기
                order_id = cursor.lastrowid

                # 2. order_items 테이블에 각 메뉴 저장
                item_sql = """
                           INSERT INTO order_items (order_id, menu_id, menu_name, price, quantity, temp)
                           VALUES (%s, %s, %s, %s, %s, %s) \
                           """

                for order in orders:
                    cursor.execute(item_sql, (
                        order_id,
                        order["menu_id"],
                        order["menu_item"],
                        order["price"],
                        order["quantity"],
                        order["temp"]
                    ))

                # 트랜잭션 커밋
                connection.commit()

                logger.info(f"주문 저장 완료: order_id={order_id}, total_price={total_price}원, phone={phone_number}")
                return order_id

        finally:
            connection.close()

    except Exception as e:
        logger.error(f"MySQL 주문 저장 실패: {e}")
        raise OrderParsingException("주문 저장 중 오류가 발생했습니다")