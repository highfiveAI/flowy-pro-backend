from sqlalchemy import Column, String, Text, DateTime, TIMESTAMP, ForeignKey, BOOLEAN
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid
from .base import Base

class Feedback(Base):
    __tablename__ = 'feedback'

    feedback_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    meeting_id = Column(UUID(as_uuid=True), ForeignKey('meeting.meeting_id'), nullable=False)
    feedbacktype_id = Column(UUID(as_uuid=True), ForeignKey('feedbacktype.feedbacktype_id'), nullable=False)
    feedback_detail = Column(JSONB, nullable=False) # Assuming JSONB based on the ERD's 'JSONB' notation for similar fields
    feedback_created_date = Column(TIMESTAMP, nullable=False)

    meeting = relationship("Meeting", back_populates="feedbacks")
    feedbacktype = relationship("FeedbackType", back_populates="feedbacks") 