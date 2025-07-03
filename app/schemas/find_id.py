from pydantic import BaseModel, EmailStr, constr

class EmailRequest(BaseModel):
    email: EmailStr

class CodeRequest(BaseModel):
    input_code: str

class CodeWithIdAndEmailRequest(BaseModel):
    user_login_id: str
    email: EmailStr
    input_code: str

class VerifyCodeResponse(BaseModel):
    verified: bool

class VerifiedPwTokenPayload(BaseModel):
    user_login_id: str
    email: EmailStr

class PasswordChangeRequest(BaseModel):
    new_password: constr(min_length=8, max_length=16)

class PasswordChangeResponse(BaseModel):
    success: bool
    message: str

class PasswordChangeEmailRequest(BaseModel):
    user_login_id: str
    email: EmailStr