import os, time, jwt
from fastapi import HTTPException, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from starlette import status

ADMIN_ID = os.getenv("ADMIN_ID", "owner_test")
ADMIN_PW = os.getenv("ADMIN_PASSWORD", "supersecret123")
JWT_SECRET = os.getenv("JWT_SECRET", "change_me_in_prod")
JWT_ALG = "HS256"
JWT_EXPIRES_MIN = int(os.getenv("JWT_EXPIRES_MIN", "120"))

bearer = HTTPBearer(auto_error=True)

def create_access_token(sub: str) -> str:
    now = int(time.time())
    payload = {
        "sub": sub,
        "role": "OWNER",
        "iss": "fastapi-auth",
        "iat": now,
        "exp": now + (JWT_EXPIRES_MIN * 60),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)

def verify_token(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

def get_current_owner(creds: HTTPAuthorizationCredentials = Depends(bearer)) -> dict:
    claims = verify_token(creds.credentials)
    if claims.get("role") != "OWNER":
        raise HTTPException(status_code=403, detail="Owner role required")
    return claims

def validate_owner_login(username: str, password: str) -> bool:
    return username == ADMIN_ID and password == ADMIN_PW
