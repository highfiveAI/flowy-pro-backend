from typing import List, Optional
from uuid import UUID
from fastapi import HTTPException, status
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.models.flowy_user import FlowyUser

# .env 파일에서 DB 설정 로드
load_dotenv()

# DB 연결 설정
DB_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/flowy_db")
engine = create_engine(
    DB_URL,
    connect_args={'options': '-c client_encoding=utf8'}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class UserCRUD:
    def __init__(self):
        self.db: Session = SessionLocal()

    def __del__(self):
        if hasattr(self, 'db'):
            self.db.close()

    def create(self, user_data: dict) -> FlowyUser:
        """새로운 사용자를 생성합니다."""
        try:
            # 이메일 중복 검사
            if self._get_user_by_email(user_data["user_email"]):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="이미 등록된 이메일입니다."
                )

            # 로그인 ID 중복 검사
            if self._get_user_by_login_id(user_data["user_login_id"]):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="이미 사용 중인 로그인 ID입니다."
                )

            user = FlowyUser(**user_data)
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)
            return user
        except Exception as e:
            self.db.rollback()
            raise e

    def get_by_id(self, user_id: UUID) -> FlowyUser:
        """ID로 사용자를 조회합니다."""
        user = self.db.query(FlowyUser).filter(FlowyUser.user_id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="사용자를 찾을 수 없습니다."
            )
        return user

    def get_all(self, skip: int = 0, limit: int = 100) -> List[FlowyUser]:
        """모든 사용자를 조회합니다."""
        return self.db.query(FlowyUser).offset(skip).limit(limit).all()

    def update(self, user_id: UUID, user_data: dict) -> FlowyUser:
        """사용자 정보를 수정합니다."""
        try:
            user = self.get_by_id(user_id)

            # 이메일 중복 검사
            if "user_email" in user_data:
                existing_user = self._get_user_by_email(user_data["user_email"])
                if existing_user and existing_user.user_id != user_id:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="이미 등록된 이메일입니다."
                    )

            # 로그인 ID 중복 검사
            if "user_login_id" in user_data:
                existing_user = self._get_user_by_login_id(user_data["user_login_id"])
                if existing_user and existing_user.user_id != user_id:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="이미 사용 중인 로그인 ID입니다."
                    )

            for key, value in user_data.items():
                setattr(user, key, value)

            self.db.commit()
            self.db.refresh(user)
            return user
        except Exception as e:
            self.db.rollback()
            raise e

    def delete(self, user_id: UUID) -> None:
        """사용자를 삭제합니다."""
        try:
            user = self.get_by_id(user_id)
            self.db.delete(user)
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            raise e

    def _get_user_by_email(self, email: str) -> Optional[FlowyUser]:
        """이메일로 사용자를 조회합니다."""
        return self.db.query(FlowyUser).filter(FlowyUser.user_email == email).first()

    def _get_user_by_login_id(self, login_id: str) -> Optional[FlowyUser]:
        """로그인 ID로 사용자를 조회합니다."""
        return self.db.query(FlowyUser).filter(FlowyUser.user_login_id == login_id).first() 