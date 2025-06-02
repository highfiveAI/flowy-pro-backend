from sqlalchemy import Column, String, Text, DateTime, TIMESTAMP, ForeignKey, BOOLEAN
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from .base import Base

class Role(Base):
    __tablename__ = 'role'

    role_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    role_name = Column(String(50), nullable=False)
    role_detail = Column(String(1000), nullable=True)

    project_users = relationship("ProjectUser", back_populates="role")
    meeting_users = relationship("Role", back_populates="role") 