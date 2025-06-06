from sqlalchemy import Column, String, Text, DateTime, TIMESTAMP, ForeignKey, BOOLEAN
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
from .base import Base

class Sysrole(Base):
    __tablename__ = 'sysrole'

    sysrole_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sysrole_name = Column(String(50), nullable=False)
    sysrole_detail = Column(String(1000), nullable=False)
    permissions = Column(Text, nullable=False)

    admins = relationship("Admin", back_populates="sysrole")
    users = relationship("FlowyUser", back_populates="sysrole")
