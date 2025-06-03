from sqlalchemy import Column, String, Text, DateTime, TIMESTAMP, ForeignKey, BOOLEAN
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid
from .base import Base

class TaskAssignLog(Base):
    __tablename__ = 'task_assign_log'

    task_assign_log_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    meeting_id = Column(UUID(as_uuid=True), ForeignKey('meeting.meeting_id'), nullable=True)
    updated_task_assign_contents = Column(JSONB, nullable=False)
    updated_task_assign_date = Column(TIMESTAMP, nullable=False)

    meeting = relationship("Meeting", back_populates="task_assign_logs") 