from sqlalchemy import Column, String, Text, ForeignKey, Boolean, TIMESTAMP, Date
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from app.models.base import Base  # Base는 declarative_base()로 정의된 객체입니다.

class Calendar(Base):
    __tablename__ = "calendar"

    calendar_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('flowy_user.user_id'), nullable=False)
    project_id = Column(UUID(as_uuid=True), ForeignKey('project.project_id'), nullable=False)
    title = Column(String(100), nullable=False)
    start = Column(TIMESTAMP, nullable=False)
    end = Column(TIMESTAMP)
    calendar_type = Column(String(100), nullable=False)
    completed = Column(Boolean, nullable=False)
    created_at = Column(TIMESTAMP, nullable=False)
    updated_at = Column(TIMESTAMP)

    users = relationship("FlowyUser", back_populates="calendar")
    project = relationship("Project", back_populates="calendar")