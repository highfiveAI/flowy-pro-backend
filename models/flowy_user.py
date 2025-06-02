from sqlalchemy import Column, String, Text, DateTime, TIMESTAMP, ForeignKey, BOOLEAN
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from .base import Base

class FlowyUser(Base):
    __tablename__ = 'flowy_user'

    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_name = Column(String(60), nullable=False)
    user_email = Column(String(255), nullable=False, unique=True)
    user_login_id = Column(String(50), nullable=False, unique=True)
    user_password = Column(String(255), nullable=False)
    user_phonenum = Column(String(20), nullable=False)
    user_company_id = Column(UUID(as_uuid=True), ForeignKey('company.company_id'), nullable=False)
    user_dept_name = Column(String(100), nullable=True)
    user_team_name = Column(String(100), nullable=True)
    user_position_id = Column(UUID(as_uuid=True), ForeignKey('company_position.position_id'), nullable=False)
    user_jobname = Column(String(100), nullable=True)
    user_sysrole_id = Column(UUID(as_uuid=True), ForeignKey('sysrole.sysrole_id'), nullable=False)

    company = relationship("Company")
    position = relationship("CompanyPosition")
    sysrole = relationship("Sysrole") 