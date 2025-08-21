from pydantic import BaseModel

class PhoneChoiceRequest(BaseModel):
    wants_phone: bool  # True: 전화번호 입력, False: 바로 완료

class PhoneInputRequest(BaseModel):
    phone_number: str
