from sqlalchemy import Column, String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from app.models.base import Base

class CompanyPosition(Base):
    __tablename__ = "company_position"

    position_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    position_company_id = Column(UUID(as_uuid=True), ForeignKey('company.company_id'), nullable=False)
    position_code = Column(String(50), nullable=False)
    position_name = Column(String(100), nullable=False)
    position_detail = Column(Text)

    users = relationship("FlowyUser", back_populates="position")
    company = relationship("Company", back_populates="company_positions")