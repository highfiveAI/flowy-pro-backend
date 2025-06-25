from pydantic import BaseModel
from typing import List, Dict, Any
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

class ProjectNameUpdate(BaseModel):
    project_name: str

# 역할 분배 insert
class TaskAssignLogCreate(BaseModel):
    meeting_id: UUID
    updated_task_assign_contents: Dict[str, Any]

class SummaryLogCreate(BaseModel):
    meeting_id: UUID
    updated_summary_contents: Dict[str, List[str]]

class ProjectUserUpdate(BaseModel):
    user_id: UUID
    role_id: UUID

class ProjectUpdateRequestBody(BaseModel):
    project_id: UUID
    project_name: str
    project_detail: str
    project_users: List[ProjectUserUpdate]

class SummaryAndTaskRequest(BaseModel):
    meeting_id: UUID
    updated_summary_contents: Dict[str, Any]
    updated_task_assign_contents: Dict[str, Any]

    class Config:
        orm_mode = True

class MeetingUserCreateRequest(BaseModel):
    user_id: str  # UUID로 받을 경우 UUID로 변경

class MeetingCreateRequest(BaseModel):
    project_id: str
    meeting_title: str
    meeting_agenda: str
    meeting_date: str  # ISO 포맷 문자열로 받음
    meeting_audio_path: str = None
    users: List[MeetingUserCreateRequest]

