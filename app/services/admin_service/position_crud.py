from typing import List, Optional
from uuid import UUID
from fastapi import HTTPException, status
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.models.company_position import CompanyPosition

# DB 연결 설정
DB_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/flowy_db")
engine = create_engine(
    DB_URL,
    connect_args={'options': '-c client_encoding=utf8'}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class PositionCRUD:
    def __init__(self):
        self.db: Session = SessionLocal()

    def __del__(self):
        if hasattr(self, 'db'):
            self.db.close()

    def create(self, position_data: dict) -> CompanyPosition:
        """새로운 직급을 생성합니다."""
        try:
            # 직급 코드 중복 검사
            if self._get_position_by_code(position_data["position_code"]):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="이미 등록된 직급 코드입니다."
                )

            position = CompanyPosition(**position_data)
            self.db.add(position)
            self.db.commit()
            self.db.refresh(position)
            return position
        except Exception as e:
            self.db.rollback()
            raise e

    def get_by_id(self, position_id: UUID) -> CompanyPosition:
        """ID로 직급을 조회합니다."""
        position = self.db.query(CompanyPosition).filter(
            CompanyPosition.position_id == position_id
        ).first()
        if not position:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="직급을 찾을 수 없습니다."
            )
        return position

    def get_all(self, skip: int = 0, limit: int = 100) -> List[CompanyPosition]:
        """모든 직급을 조회합니다."""
        return self.db.query(CompanyPosition).offset(skip).limit(limit).all()

    def update(self, position_id: UUID, position_data: dict) -> CompanyPosition:
        """직급 정보를 수정합니다."""
        try:
            position = self.get_by_id(position_id)

            # 직급 코드 중복 검사
            if "position_code" in position_data:
                existing_position = self._get_position_by_code(
                    position_data["position_code"]
                )
                if existing_position and existing_position.position_id != position_id:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="이미 등록된 직급 코드입니다."
                    )

            for key, value in position_data.items():
                setattr(position, key, value)

            self.db.commit()
            self.db.refresh(position)
            return position
        except Exception as e:
            self.db.rollback()
            raise e

    def delete(self, position_id: UUID) -> None:
        """직급을 삭제합니다."""
        try:
            position = self.get_by_id(position_id)
            self.db.delete(position)
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            raise e

    def _get_position_by_code(self, code: str) -> Optional[CompanyPosition]:
        """직급 코드로 직급을 조회합니다."""
        return self.db.query(CompanyPosition).filter(
            CompanyPosition.position_code == code
        ).first() 