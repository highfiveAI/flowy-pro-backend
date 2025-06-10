from sqlalchemy import Column, String, Boolean, TIMESTAMP, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
from app.models.base import Base

class SignupLog(Base):
    __tablename__ = 'signup_log'
    signup_log_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    signup_request_user_id = Column(UUID(as_uuid=True), ForeignKey("flowy_user.user_id"), nullable=False)
    signup_update_user_id = Column(UUID(as_uuid=True), ForeignKey("flowy_user.user_id"), nullable=False)
    signup_status_changed_date = Column(TIMESTAMP, nullable=True)
    signup_completed_status = Column(String(20), nullable=False)


    # 관계 정의
    signup_request_user = relationship("FlowyUser", foreign_keys=[signup_request_user_id], back_populates="signup_request_logs")
    signup_update_user = relationship("FlowyUser", foreign_keys=[signup_update_user_id], back_populates="signup_update_logs")
