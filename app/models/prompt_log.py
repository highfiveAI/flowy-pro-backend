# models.py
from sqlalchemy import Column, String, Text, TIMESTAMP, Enum, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
from .base import Base

class PromptLog(Base):
    __tablename__ = 'prompt_log'

    prompt_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    prompt_meeting_id = Column(UUID(as_uuid=True), ForeignKey('meeting.meeting_id'), nullable=False)
    agent_type = Column(Enum('search', 'summary', 'docs', name='agent_type_enum'), nullable=False)
    prompt_output = Column(Text, nullable=False)
    prompt_input_date = Column(TIMESTAMP(timezone=True), nullable=False)
    prompt_output_date = Column(TIMESTAMP(timezone=True), nullable=False)

    meeting = relationship("Meeting", back_populates="prompt_logs")