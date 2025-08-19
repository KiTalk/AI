# config/swagger_config.py
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import Depends
import os

# JWT Bearer 토큰 스키마
security = HTTPBearer()

def custom_openapi(app: FastAPI):
    """커스텀 OpenAPI 스키마 생성"""
    if app.openapi_schema:
        return app.openapi_schema

    # 서버 정보 설정
    context_path = os.getenv("CONTEXT_PATH", "")

    openapi_schema = get_openapi(
        title="KiTalk API 명세서",
        version="1.0",
        description="KiTalk Swagger API Documentation",
        routes=app.routes,
        servers=[
            {
                "url": context_path,
                "description": "KiTalk Server"
            }
        ]
    )

    if "components" not in openapi_schema:
        openapi_schema["components"] = {}


    # JWT Bearer 인증 스키마 추가
    openapi_schema["components"]["securitySchemes"] = {
        "bearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT"
        }
    }

    # 전역 보안 요구사항 설정
    openapi_schema["security"] = [{"bearerAuth": []}]

    app.openapi_schema = openapi_schema
    return app.openapi_schema


def setup_swagger(app: FastAPI):
    """Swagger 설정 적용"""
    app.openapi = lambda: custom_openapi(app)

    # Swagger UI 및 ReDoc 설정
    app.docs_url = "/swagger-ui"  # Swagger UI 경로
    app.redoc_url = "/redoc"  # ReDoc 경로
    app.openapi_url = "/openapi.json"  # OpenAPI JSON 경로


# main.py에서 사용할 설정 함수
def create_app() -> FastAPI:
    """FastAPI 앱 생성 및 설정"""
    app = FastAPI(
        title="KiTalk API",
        description="KiTalk Swagger API Documentation",
        version="1.0",
        docs_url=None,  # 커스텀 설정을 위해 기본값 비활성화
        redoc_url=None
    )

    # Swagger 설정 적용
    setup_swagger(app)

    return app


# JWT 토큰 의존성 (필요한 엔드포인트에서 사용)
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """JWT 토큰 검증 의존성"""
    token = credentials.credentials
    # 여기에 JWT 토큰 검증 로직 추가
    # decode_jwt_token(token) 등
    return {"user_id": "example", "token": token}