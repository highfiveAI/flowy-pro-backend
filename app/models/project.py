from sqlalchemy import Column, String, Text, DateTime, TIMESTAMP, ForeignKey, BOOLEAN
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from .base import Base

class Project(Base):
    __tablename__ = 'project'

    project_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey('company.company_id'), nullable=False)
    project_name = Column(String(200), nullable=False)
    project_detail = Column(Text, nullable=True)
    project_created_date = Column(DateTime, nullable=False)
    project_updated_date = Column(DateTime, nullable=True)
    project_end_date = Column(DateTime, nullable=True)
    project_status = Column(BOOLEAN, nullable=False)

    company = relationship("Company", back_populates="projects")
    project_users = relationship("ProjectUser", back_populates="project")
    meetings = relationship("Meeting", back_populates="project")
    calendar = relationship("Calendar", back_populates="project")

