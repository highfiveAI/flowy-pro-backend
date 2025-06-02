from sqlalchemy import Column, String, Text, DateTime, TIMESTAMP, ForeignKey, BOOLEAN
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid
from .base import Base

class SummaryLog(Base):
    __tablename__ = 'summary_log'

    summary_log_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    meeting_id = Column(UUID(as_uuid=True), ForeignKey('meeting.meeting_id'), nullable=True)
    updated_summary_contents = Column(JSONB, nullable=False)
    updated_summary_date = Column(TIMESTAMP, nullable=False)

    meeting = relationship("Meeting") 