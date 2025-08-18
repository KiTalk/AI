from fastapi import HTTPException

class SessionNotFoundException(HTTPException):
    def __init__(self, session_id: str):
        super().__init__(
            status_code=404,
            detail=f"세션을 찾을 수 없습니다: {session_id}"
        )

class SessionExpiredException(HTTPException):
    def __init__(self, session_id: str):
        super().__init__(
            status_code=401,
            detail=f"세션이 만료되었습니다: {session_id}"
        )

class InvalidSessionStepException(HTTPException):
    def __init__(self, current_step: str, required_step: str):
        super().__init__(
            status_code=400,
            detail=f"현재 단계({current_step})에서는 실행할 수 없습니다. 필요한 단계: {required_step}"
        )

class SessionUpdateFailedException(HTTPException):
    def __init__(self, session_id: str, operation: str = "업데이트"):
        super().__init__(
            status_code=500,
            detail=f"세션 {operation}에 실패했습니다: {session_id}"
        )