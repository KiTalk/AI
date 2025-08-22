from typing import List, Dict, Any, Optional, Tuple
from database.simple_db import simple_menu_db
from pymysql.cursors import DictCursor

ALLOWED_STATUSES = ("PAID", "COMPLETED")

def _ensure_conn():
    conn = simple_menu_db.get_connection()
    if conn is None:
        raise RuntimeError("Database connection failed")
    return conn

def list_orders_with_items(status: Optional[str] = None) -> List[Dict[str, Any]]:
    base_sql = """
    SELECT
        o.id               AS order_id,
        o.phone_number     AS phone_number,
        o.total_price      AS total_price,
        o.packaging_type   AS packaging_type,
        o.created_at       AS created_at,
        UPPER(o.status)    AS status,         -- 표준화
        oi.id              AS item_id,
        oi.menu_id         AS menu_id,
        oi.menu_name       AS menu_name,
        oi.price           AS item_price,
        oi.quantity        AS quantity,
        oi.temp            AS temp
    FROM orders o
    INNER JOIN order_items oi ON oi.order_id = o.id
    {where_clause}
    ORDER BY o.created_at DESC, o.id DESC, oi.id ASC
    """

    params: Tuple = ()
    where_clause = "WHERE UPPER(o.status) IN (%s, %s)"
    params += ALLOWED_STATUSES

    if status:
        status_upper = status.upper()
        if status_upper not in ALLOWED_STATUSES:
            return []
        where_clause = "WHERE UPPER(o.status) = %s"
        params = (status_upper,)

    sql = base_sql.format(where_clause=where_clause)

    conn = _ensure_conn()
    try:
        with conn.cursor(DictCursor) as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
    finally:
        conn.close()

    orders_map: Dict[int, Dict[str, Any]] = {}
    for r in rows:
        oid = r["order_id"]
        if oid not in orders_map:
            orders_map[oid] = {
                "id": oid,
                "phone_number": r.get("phone_number"),
                "total_price": r["total_price"],
                "packaging_type": r.get("packaging_type"),
                "created_at": r["created_at"],
                "status": r["status"],
                "items": [],
            }
        orders_map[oid]["items"].append(
            {
                "menu_id": r["menu_id"],
                "menu_name": r["menu_name"],
                "price": r["item_price"],
                "quantity": r["quantity"],
                "temp": r["temp"],
            }
        )

    return list(orders_map.values())


def get_order_status(order_id: int) -> Optional[str]:
    sql = "SELECT UPPER(status) AS status FROM orders WHERE id = %s"

    conn = _ensure_conn()
    try:
        with conn.cursor(DictCursor) as cur:
            cur.execute(sql, (order_id,))
            row = cur.fetchone()
            if not row:
                return None
            return row["status"]
    finally:
        conn.close()


def update_order_status(order_id: int, new_status: str) -> int:
    new_status_upper = new_status.upper()
    if new_status_upper not in ALLOWED_STATUSES:
        raise ValueError("Invalid status")

    sql = "UPDATE orders SET status = %s WHERE id = %s"

    conn = _ensure_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, (new_status_upper, order_id))
            affected = cur.rowcount
        conn.commit()
        return affected
    finally:
        conn.close()
