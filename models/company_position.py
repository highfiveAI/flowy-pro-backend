from sqlalchemy import Column, String, Text, DateTime, TIMESTAMP, ForeignKey, BOOLEAN
from sqlalchemy.dialects.postgresql import UUID
import uuid
from .base import Base

class CompanyPosition(Base):
    __tablename__ = 'company_position'

    position_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    position_code = Column(String(50), nullable=False)
    position_name = Column(String(100), nullable=False)
    position_detail = Column(Text, nullable=True) 