from fastapi import APIRouter, HTTPException
from starlette import status
from schemas.auth import OwnerLoginReq, OwnerLoginRes
from core.common.security import create_access_token, validate_owner_login

router = APIRouter(prefix="/owner", tags=["Owner"])

@router.post("/login", response_model=OwnerLoginRes, summary="점주 로그인 (JWT 발급)")
def owner_login(req: OwnerLoginReq):
    if not validate_owner_login(req.username, req.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    token = create_access_token(sub=req.username)
    return OwnerLoginRes(access_token=token)
