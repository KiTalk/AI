import time
import jwt
from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from starlette import status

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class SecuritySettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    admin_id: str = Field(..., alias="ADMIN_ID")
    admin_password: str = Field(..., alias="ADMIN_PASSWORD")
    jwt_secret: str = Field(..., alias="JWT_SECRET")
    jwt_expires_min: int = Field(1440, alias="JWT_EXPIRES_MIN")  # 분 단위, 기본 1일


S = SecuritySettings()

JWT_ALG = "HS256"
bearer = HTTPBearer(auto_error=True, scheme_name="bearerAuth")


def validate_owner_login(username: str, password: str) -> bool:
    return username == S.admin_id and password == S.admin_password


def create_access_token(sub: str) -> str:
    now = int(time.time())
    payload = {
        "sub": sub,
        "role": "OWNER",
        "iss": "fastapi-auth",
        "iat": now,
        "exp": now + (S.jwt_expires_min * 60),
    }
    return jwt.encode(payload, S.jwt_secret, algorithm=JWT_ALG)


def verify_token(token: str) -> dict:
    try:
        return jwt.decode(token, S.jwt_secret, algorithms=[JWT_ALG])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


def get_current_owner(creds: HTTPAuthorizationCredentials = Security(bearer)) -> dict:
    claims = verify_token(creds.credentials)
    if claims.get("role") != "OWNER":
        raise HTTPException(status_code=403, detail="Owner role required")
    return claims
