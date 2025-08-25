import pymysql
import logging
import json
from typing import Optional, Dict, List
import os
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class SimpleMenuDB:
    def __init__(self):
        self.connection_config = {
            'host': os.getenv("DB_HOST"),
            'port': int(os.getenv("DB_PORT")),
            'user': os.getenv("DB_USER"),
            'password': os.getenv("DB_PASSWORD"),
            'database': os.getenv("DB_NAME"),
            'charset': 'utf8mb4'
        }

# 데이터 베이스 연결 생성
    def get_connection(self):
        try:
            return pymysql.connect(**self.connection_config)
        except Exception as e:
            logger.error(f"MySQL 연결 실패: {e}")
            return None

# menu_id로 가격 조회
    def get_menu_price(self, menu_id: int) -> Optional[int]:
        connection = self.get_connection()
        if not connection:
            return None

        try:
            with connection.cursor() as cursor:
                sql = "SELECT price FROM menu WHERE id = %s AND is_active = 1"
                cursor.execute(sql, (menu_id,))
                result = cursor.fetchone()
                return result[0] if result else None

        except Exception as e:
            logger.error(f"가격 조회 실패 (menu_id: {menu_id}): {e}")
            return None
        finally:
            connection.close()

# 여러 menu_id의 가격을 한 번에 조회
    def get_multiple_menu_prices(self, menu_ids: List[int]) -> Dict[int, int]:
        if not menu_ids:
            return {}

        connection = self.get_connection()
        if not connection:
            return {}

        try:
            with connection.cursor() as cursor:
                # IN 절을 위한 플레이스홀더 생성
                placeholders = ','.join(['%s'] * len(menu_ids))
                sql = f"SELECT id, price FROM menu WHERE id IN ({placeholders}) AND is_active = 1"
                cursor.execute(sql, menu_ids)
                results = cursor.fetchall()

                return {menu_id: price for menu_id, price in results}

        except Exception as e:
            logger.error(f"가격 일괄 조회 실패 (menu_ids: {menu_ids}): {e}")
            return {}
        finally:
            connection.close()

# 연결 테스트
    def test_connection(self) -> bool:
        connection = self.get_connection()
        if not connection:
            return False

        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                logger.info("MySQL 연결 테스트 성공!")
                return result[0] == 1
        except Exception as e:
            logger.error(f"MySQL 연결 테스트 실패: {e}")
            return False
        finally:
            connection.close()

# menu_id로 profile 조회 (null이면 null 반환)
    def get_user_profile(self, menu_id: int) -> Optional[Dict]:
        connection = self.get_connection()
        if not connection:
            return None

        try:
            with connection.cursor(pymysql.cursors.DictCursor) as cursor:
                # menu 테이블에서 profile 컬럼 조회
                sql = "SELECT profile FROM menu WHERE id = %s AND is_active = 1"
                cursor.execute(sql, (menu_id,))
                result = cursor.fetchone()

                if result and result['profile']:
                    logger.info(f"Profile 조회 성공: menu_id={menu_id}")
                    profile_data = result['profile']
                    
                    # profile이 JSON 문자열이면 파싱
                    if isinstance(profile_data, str):
                        try:
                            return json.loads(profile_data)
                        except json.JSONDecodeError:
                            # JSON이 아닌 일반 문자열(URL 등)이면 그대로 반환
                            return profile_data
                    else:
                        return profile_data
                else:
                    logger.info(f"Profile 없음: menu_id={menu_id}")
                    return None

        except Exception as e:
            logger.error(f"Profile 조회 실패 (menu_id: {menu_id}): {e}")
            return None
        finally:
            connection.close()

# 전역 인스턴스
simple_menu_db = SimpleMenuDB()