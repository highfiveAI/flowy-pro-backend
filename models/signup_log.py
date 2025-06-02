from sqlalchemy import Column, String, Text, DateTime, TIMESTAMP, ForeignKey, BOOLEAN
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from .base import Base

class SignupLog(Base):
    __tablename__ = 'signup_log'

    signup_log_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    signup_request_user_id = Column(UUID(as_uuid=True), ForeignKey('flowy_user.user_id'), nullable=False)
    signup_updated_user_id = Column(UUID(as_uuid=True), ForeignKey('flowy_user.user_id'), nullable=False)
    signup_status_changed_date = Column(TIMESTAMP, nullable=True)
    signup_completed_status = Column(BOOLEAN, nullable=False)

    request_user = relationship("FlowyUser", foreign_keys=[signup_request_user_id])
    updated_user = relationship("FlowyUser", foreign_keys=[signup_updated_user_id]) 