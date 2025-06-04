from sqlalchemy import Column, String, Text, TIMESTAMP, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from pgvector.sqlalchemy import Vector
import uuid
from app.models.base import Base

class ProfileImg(Base):
    __tablename__ = "profile_img"

    profile_img_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("flowy_user.user_id"), nullable=False)
    profile_img_name= Column(String(100), nullable=False)
    profile_img_path= Column(Text, nullable=False)
    profile_img_uploaded_date = Column(TIMESTAMP, nullable=False)

    user = relationship("FlowyUser", back_populates="profile_imgs")