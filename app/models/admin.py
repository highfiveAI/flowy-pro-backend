from sqlalchemy import Column, String, Text, DateTime, TIMESTAMP, ForeignKey, BOOLEAN
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from .base import Base

class Admin(Base):
    __tablename__ = 'admin'

    admin_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    admin_company_id = Column(UUID(as_uuid=True), ForeignKey('company.company_id'), nullable=False)
    admin_sysrole_id = Column(UUID(as_uuid=True), ForeignKey('sysrole.sysrole_id'), nullable=False)

    company = relationship("Company", back_populates="admins")
    sysrole = relationship("Sysrole", back_populates="admins")