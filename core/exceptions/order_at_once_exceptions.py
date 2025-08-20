from fastapi import HTTPException

class BaseOrderAtOnceException(HTTPException):
    def __init__(self, status_code: int, detail: str):
        super().__init__(status_code=status_code, detail=detail)

class MenuNotRecognizedException(BaseOrderAtOnceException):
    def __init__(self, order_text: str = ""):
        super().__init__(
            status_code=404,
            detail=f"메뉴를 인식하지 못했습니다. 입력: '{order_text}'"
        )

class PackagingNotRecognizedException(BaseOrderAtOnceException):
    def __init__(self, order_text: str = ""):
        super().__init__(
            status_code=404,
            detail=f"포장 여부를 인식하지 못했습니다. 입력: '{order_text}'"
        )

class QuantityNotRecognizedException(BaseOrderAtOnceException):
    def __init__(self, order_text: str = ""):
        super().__init__(
            status_code=404,
            detail=f"수량을 인식하지 못했습니다. 입력: '{order_text}'"
        )

class OrderParsingException(BaseOrderAtOnceException):
    def __init__(self, order_text: str = ""):
        super().__init__(
            status_code=400,
            detail=f"주문을 해석할 수 없습니다: '{order_text}'"
        )

class OrderNotRecognizedException(BaseOrderAtOnceException):
    def __init__(self, order_text: str = ""):
        super().__init__(
            status_code=400,
            detail="다시 말씀해주세요"
        )
