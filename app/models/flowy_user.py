from sqlalchemy import Column, String, Boolean, TIMESTAMP, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
from app.models.base import Base  # Base는 declarative_base()로 정의된 객체입니다.

class User(Base):
    __tablename__ = 'flowy_user'
    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_name = Column(String(50), nullable=False)
    user_email = Column(String(255), nullable=False) 
    user_login_id = Column(String(50), nullable=False)
    user_password = Column(String(255), nullable=False)
    user_phonenum = Column(String(20), nullable=False)
    user_company_id = Column(String(36), nullable=False)
    user_dept_name = Column(String(100))
    user_team_name = Column(String(100))
    user_position_id = Column(String(36), nullable=False)
    user_jobname = Column(String(100))
    user_sysrole_id = Column(String(36), nullable=False)

    # 관계 정의
    # profile_image = relationship("ProfileImg", back_populates="user", uselist=False)
