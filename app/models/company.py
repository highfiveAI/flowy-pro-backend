from sqlalchemy import Column, String, Text, DateTime, TIMESTAMP, ForeignKey, BOOLEAN
from sqlalchemy.dialects.postgresql import UUID
import uuid
from sqlalchemy.orm import relationship
from .base import Base

class Company(Base):
    __tablename__ = 'company'

    company_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_name = Column(String(150), nullable=False)
    company_scale = Column(String(100), nullable=True)
    service_startdate = Column(TIMESTAMP, nullable=True)
    service_enddate = Column(TIMESTAMP, nullable=True)
    service_status = Column(BOOLEAN, nullable=False)

    sysroles = relationship("Sysrole", back_populates="company")
    users = relationship("FlowyUser", back_populates="company")