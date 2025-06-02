from sqlalchemy import Column, String, Text, DateTime, TIMESTAMP, ForeignKey, BOOLEAN
from sqlalchemy.dialects.postgresql import UUID
import uuid
from .base import Base

class FeedbackType(Base):
    __tablename__ = 'feedback_type'

    feedbacktype_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    feedbacktype_name = Column(String(100), nullable=False)
    feedback_detail = Column(Text, nullable=False) # Assuming TEXT based on the ERD

# ... existing code ... 