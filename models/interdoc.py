from sqlalchemy import Column, String, Text, DateTime, TIMESTAMP, ForeignKey, BOOLEAN, LargeBinary
from sqlalchemy.dialects.postgresql import UUID, JSONB, VECTOR
from sqlalchemy.orm import relationship
import uuid
from .base import Base

class Interdoc(Base):
    __tablename__ = 'interdocs'

    interdoc_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    interdoc_type_name = Column(String(50), nullable=False)
    interdoc_filename = Column(String(100), nullable=False)
    interdoc_contents = Column(String(255), nullable=False) # VARCHAR(255)
    # Assuming VECTOR type might need a specific SQLAlchemy extension or custom type
    # For now, representing it as LargeBinary or consider using sqlalchemy-utils Vector type if available
    interdoc_vector = Column(LargeBinary) # Placeholder for VECTOR type
    interdoc_path = Column(Text, nullable=False)
    interdoc_uploaded_date = Column(TIMESTAMP, nullable=False)
    interdoc_updated_date = Column(TIMESTAMP, nullable=True)
    interdoc_update_user_id = Column(UUID(as_uuid=True), ForeignKey('flowy_user.user_id'), nullable=True)

    update_user = relationship("FlowyUser") 