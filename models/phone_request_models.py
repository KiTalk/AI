from pydantic import BaseModel

class PhoneChoiceRequest(BaseModel):
    wants_phone: bool

class PhoneInputRequest(BaseModel):
    phone_number: str
