from sqlalchemy import Column, String, Text, DateTime, TIMESTAMP, ForeignKey, BOOLEAN
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from .base import Base

class Meeting(Base):
    __tablename__ = 'meeting'

    meeting_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey('project.project_id'), nullable=False)
    meeting_title = Column(String(150), nullable=False)
    meeting_agenda = Column(String(1000), nullable=True)
    meeting_date = Column(TIMESTAMP, nullable=False)
    meeting_audio_path = Column(Text, nullable=False)
    meeting_audio_type = Column(String(30), nullable=False)

    project = relationship("Project") 