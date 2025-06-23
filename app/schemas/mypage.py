from pydantic import BaseModel
from typing import Optional
from uuid import UUID

class UserUpdateRequest(BaseModel):
    # user_team_name: Optional[str] = None
    # user_dept_name: Optional[str] = None
    user_name: Optional[str] = None
    user_password: Optional[str] = None
    user_phonenum: Optional[str] = None

class UserWithCompanyInfo(BaseModel):
    user_id: UUID
    user_name: str
    user_email: str
    user_login_id: str
    user_phonenum: Optional[str] = None
    user_team_name: Optional[str] = None
    user_dept_name: Optional[str] = None
    company_id: Optional[UUID] = None
    company_name: Optional[str] = None
