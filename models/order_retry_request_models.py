from pydantic import BaseModel, Field, validator

class MenuRetryRequest(BaseModel):
    text: str = Field(..., description="손님이 다시 말한 문장 (메뉴만 재인식)")

class PackagingRetryRequest(BaseModel):
    packaging: str = Field(..., description="포장/매장 여부 ('포장' 또는 '매장식사')")

    @validator("packaging")
    def _validate_packaging(cls, v: str):
        val = (v or "").strip()
        if val not in {"포장", "매장식사"}:
            raise ValueError("packaging은 '포장' 또는 '매장식사'만 허용됩니다.")
        return val

class TempRetryRequest(BaseModel):
    temp: str = Field(..., description="음료 온도 ('hot' 또는 'ice')")

    @validator("temp")
    def _validate_temp(cls, v: str):
        val = (v or "").lower().strip()
        if val not in {"hot", "ice"}:
            raise ValueError("temp는 'hot' 또는 'ice'만 허용됩니다.")
        return val
