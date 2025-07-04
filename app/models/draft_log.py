from sqlalchemy import Column, String, Text, TIMESTAMP, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from .base import Base

class DraftLog(Base):
    __tablename__ = 'draft_log'

    draft_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    meeting_id = Column(UUID(as_uuid=True), ForeignKey('meeting.meeting_id'))
    draft_trigger = Column(Text, nullable=True)
    docs_source_type = Column(Enum('internal', 'external', name='docs_source_type'), nullable=True)
    ref_interdoc_id = Column(String(512), nullable=True)
    ref_external_link = Column(Text, nullable=True)
    draft_title = Column(String(100), nullable=True)
    draft_url = Column(Text, nullable=True)
    draft_ref_reason = Column(Text, nullable=False)
    draft_created_date = Column(TIMESTAMP, nullable=False)

    meeting = relationship("Meeting", back_populates="draft_logs")
