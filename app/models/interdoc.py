from sqlalchemy import Column, String, Text, TIMESTAMP, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from pgvector.sqlalchemy import Vector
import uuid
from app.models.base import Base

class Interdoc(Base):
    __tablename__ = "interdocs"

    interdocs_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    interdocs_type_name = Column(String(50), nullable=False)
    interdocs_filename = Column(String(100), nullable=False)
    interdocs_contents = Column(String(255), nullable=False)
    interdocs_vector = Column(Vector(1536), nullable=False)
    interdocs_path = Column(Text, nullable=False)
    interdocs_uploaded_date = Column(TIMESTAMP, nullable=False)
    interdocs_updated_date = Column(TIMESTAMP, nullable=True)
    interdocs_update_user_id = Column(UUID(as_uuid=True), ForeignKey("flowy_user.user_id"), nullable=False)

    user = relationship("FlowyUser", back_populates="interdocs")