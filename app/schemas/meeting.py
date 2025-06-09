from pydantic import BaseModel, UUID4
from typing import Optional, Dict
from datetime import datetime

# 회의 테이블
class MeetingBase(BaseModel):
    project_id: UUID4
    meeting_title: str
    meeting_agenda: Optional[str] = None
    meeting_date: datetime
    meeting_audio_path: Optional[str] = None
    meeting_audio_type: Optional[str] = None

class MeetingCreate(MeetingBase):
    pass

class MeetingUpdate(MeetingBase):
    pass

class MeetingResponse(MeetingBase):
    meeting_id: UUID4
    class Config:
        from_attributes = True

# 요약 로그
class SummaryLogBase(BaseModel):
    meeting_id: UUID4
    updated_summary_contents: Dict
    updated_summary_date: datetime

class SummaryLogCreate(SummaryLogBase):
    pass

class SummaryLogResponse(SummaryLogBase):
    summary_log_id: UUID4
    class Config:
        from_attributes = True

# 역할분담 로그
class TaskAssignLogBase(BaseModel):
    meeting_id: UUID4
    updated_task_assign_contents: Dict
    updated_task_assign_date: datetime

class TaskAssignLogCreate(TaskAssignLogBase):
    pass

class TaskAssignLogResponse(TaskAssignLogBase):
    task_assign_log_id: UUID4
    class Config:
        from_attributes = True

# 피드백
class FeedbackBase(BaseModel):
    meeting_id: UUID4
    feedbacktype_id: Optional[UUID4] = None
    feedback_detail: str
    feedback_created_date: datetime

class FeedbackCreate(FeedbackBase):
    pass

class FeedbackResponse(FeedbackBase):
    feedback_id: UUID4
    class Config:
        from_attributes = True