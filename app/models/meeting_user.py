from sqlalchemy import Column, String, Text, DateTime, TIMESTAMP, ForeignKey, BOOLEAN
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from .base import Base

class MeetingUser(Base):
    __tablename__ = 'meeting_user'

    meeting_user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('flowy_user.user_id'), nullable=False)
    meeting_id = Column(UUID(as_uuid=True), ForeignKey('meeting.meeting_id'), nullable=False)
    role_id = Column(UUID(as_uuid=True), ForeignKey('role.role_id'), nullable=False)

    user = relationship("FlowyUser", back_populates="meeting_users")
    meeting = relationship("Meeting", back_populates="meeting_users")
    role = relationship("Role", back_populates="meeting_users") 