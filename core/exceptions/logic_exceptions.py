from fastapi import HTTPException

class MenuNotFoundException(HTTPException):
    def __init__(self, menu_name: str):
        super().__init__(
            status_code=404,
            detail=f"'{menu_name}' 메뉴를 찾을 수 없습니다."
        )

class OrderParsingException(HTTPException):
    def __init__(self, order_text: str):
        super().__init__(
            status_code=400,
            detail=f"주문을 해석할 수 없습니다: '{order_text}'"
        )

class PackagingNotFoundException(HTTPException):
    def __init__(self, packaging_type: str):
        super().__init__(
            status_code=404,
            detail=f"포장 방식을 인식할 수 없습니다: '{packaging_type}'"
        )

class MultipleOrdersException(HTTPException):
    def __init__(self, failed_orders: list):
        super().__init__(
            status_code=400,
            detail=f"다음 주문에 문제가 있습니다: {', '.join(failed_orders)}"
        )

class BaseOrderException(HTTPException):
    def __init__(self, status_code: int, detail: str):
        super().__init__(status_code=status_code, detail=detail)

class OrderNotRecognizedException(BaseOrderException):
    def __init__(self, order_text: str):
        super().__init__(
            status_code=400,
            detail=f"다시 말씀해주세요"
        )