from sqlalchemy import Column, String, Text, DateTime, TIMESTAMP, ForeignKey, BOOLEAN
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from .base import Base

class Meeting(Base):
    __tablename__ = 'meeting'

    meeting_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey('project.project_id', ondelete="CASCADE"), nullable=False)
    meeting_title = Column(String(150), nullable=False)
    meeting_agenda = Column(String(1000), nullable=True)
    meeting_date = Column(TIMESTAMP, nullable=False)
    meeting_audio_path = Column(Text, nullable=False)
    parent_meeting_id = Column(String(255), nullable=True)  # 원본회의 ID (후속회의인 경우)
    # meeting_audio_type = Column(String(30), nullable=False)

    project = relationship("Project", back_populates="meetings")
    summary_logs = relationship("SummaryLog", back_populates="meeting")
    task_assign_logs = relationship("TaskAssignLog", back_populates="meeting")
    meeting_users = relationship("MeetingUser", back_populates="meeting")
    draft_logs = relationship("DraftLog", back_populates="meeting")
    feedbacks = relationship("Feedback", back_populates="meeting")
    prompt_logs = relationship("PromptLog", back_populates="meeting")   
    calendars = relationship("Calendar", back_populates="meeting")