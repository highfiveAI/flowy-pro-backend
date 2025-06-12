from pydantic import BaseModel
from typing import Optional

class UserUpdateRequest(BaseModel):
    user_team_name: Optional[str] = None
    user_dept_name: Optional[str] = None
    user_phonenum: Optional[str] = None