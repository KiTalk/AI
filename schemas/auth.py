from pydantic import BaseModel

class OwnerLoginReq(BaseModel):
    username: str
    password: str

class OwnerLoginRes(BaseModel):
    access_token: str
    token_type: str = "bearer"
