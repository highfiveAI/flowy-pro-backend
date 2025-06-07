from pydantic import BaseModel, EmailStr

# 응답용 스키마
class User(BaseModel):
    id: int
    name: str
    email: EmailStr
    phone: str
    login_id: str
    company: str
    department: str | None = None
    team: str | None = None

    class Config:
        orm_mode = True

# 사용자 생성용 스키마
class UserCreate(BaseModel):
    name: str
    email: EmailStr 
    login_id: str
    password: str
    phone: str
    company: str
    department: str | None = None
    team: str | None = None
    position: str
    job: str
    sysrole: str

# 소셜 회원가입 생성용 스키마
class SocialUserCreate(BaseModel):
    login_id: str
    password: str
    phone: str
    company: str
    department: str | None = None
    team: str | None = None
    position: str
    job: str
    sysrole: str

class LoginInfo(BaseModel):
    email: EmailStr
    password: str

    class Config:
        orm_mode = True