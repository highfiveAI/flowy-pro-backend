from pydantic import BaseModel
from typing import List
from uuid import UUID

class UserSchema(BaseModel):
    user_name: str
    user_id: UUID

class RoleSchema(BaseModel):
    role_name: str
    role_id: UUID

class ProjectUserCreate(BaseModel):
    user_id: UUID
    role_id: UUID

class ProjectCreate(BaseModel):
    company_id: UUID
    project_name: str
    project_detail: str
    project_status: bool
    project_users: List[ProjectUserCreate]

    class Config:
        orm_mode = True

