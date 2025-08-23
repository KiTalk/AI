from typing import Optional, Tuple
import logging
from database.simple_db import simple_menu_db

logger = logging.getLogger(__name__)

def find_menu_id_by_name_temp(name: str, temperature: str) -> Optional[int]:
    conn = simple_menu_db.get_connection()
    if not conn:
        return None
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM menu WHERE name=%s AND temperature=%s LIMIT 1",
                (name, temperature)
            )
            row = cur.fetchone()
            return int(row[0]) if row else None
    except Exception as e:
        logger.error(f"[owner_menu_repo] find_menu_id_by_name_temp error: {e}")
        return None
    finally:
        conn.close()

def insert_menu_tx(conn, name: str, temperature: str, price: int, category: str,
                   popular: bool, profile: Optional[str]) -> Tuple[bool, Optional[int], Optional[str]]:
    try:
        with conn.cursor() as cur:
            sql = """
            INSERT INTO menu (name, temperature, price, category, popular, profile)
            VALUES (%s, %s, %s, %s, %s, %s)
            """
            cur.execute(sql, (name, temperature, price, category, int(popular), profile))
            new_id = cur.lastrowid  # AUTO_INCREMENT id
            return True, int(new_id), None
    except Exception as e:
        logger.error(f"[owner_menu_repo] insert_menu_tx error: {e}")
        return False, None, str(e)
