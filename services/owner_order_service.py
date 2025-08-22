from typing import List, Dict, Any, Optional
from database.repositories.orders_repo import (
    list_orders_with_items,
    get_order_status,
    update_order_status,
)

class NotFoundError(Exception):
    pass

class ConflictError(Exception):
    pass

ALLOWED_STATUSES = ("PAID", "COMPLETED")

def service_list_orders(status: Optional[str] = None) -> List[Dict[str, Any]]:
    return list_orders_with_items(status=status)

def service_mark_completed(order_id: int) -> Dict[str, Any]:
    cur = get_order_status(order_id)
    if cur is None:
        raise NotFoundError("Order not found")
    if cur == "COMPLETED":
        raise ConflictError("Already COMPLETED")
    if cur != "PAID":
        raise ConflictError(f"Invalid transition from {cur} to COMPLETED")

    affected = update_order_status(order_id, "COMPLETED")
    if affected == 0:
        raise NotFoundError("Order not found")
    return {"id": order_id, "status": "COMPLETED"}

def service_mark_paid(order_id: int) -> Dict[str, Any]:
    cur = get_order_status(order_id)
    if cur is None:
        raise NotFoundError("Order not found")
    if cur == "PAID":
        raise ConflictError("Already PAID")
    if cur != "COMPLETED":
        raise ConflictError(f"Invalid transition from {cur} to PAID")

    affected = update_order_status(order_id, "PAID")
    if affected == 0:
        raise NotFoundError("Order not found")
    return {"id": order_id, "status": "PAID"}
