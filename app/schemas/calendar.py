from pydantic import BaseModel, UUID4
from typing import Optional
from datetime import datetime

class CalendarResponse(BaseModel):
    calendar_id: UUID4
    user_id: UUID4
    project_id: UUID4
    title: str
    start: datetime
    end: Optional[datetime] = None
    calendar_type: str  # meeting, todo 만 가능
    completed: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True 