from sqlalchemy import Column, String, Text, DateTime, TIMESTAMP, ForeignKey, BOOLEAN
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from .base import Base

class ProjectUser(Base):
    __tablename__ = 'project_user'

    project_user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('flowy_user.user_id'), nullable=False)
    project_id = Column(UUID(as_uuid=True), ForeignKey('project.project_id'), nullable=False)
    role_id = Column(UUID(as_uuid=True), ForeignKey('role.role_id'), nullable=False)

    user = relationship("FlowyUser")
    project = relationship("Project")
    role = relationship("Role") 