from typing import List, Optional
from uuid import UUID
from datetime import datetime
from fastapi import HTTPException, status
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.models.company import Company

# .env 파일에서 DB 설정 로드
load_dotenv()

# DB 연결 설정
DB_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/flowy_db")
engine = create_engine(
    DB_URL,
    connect_args={'options': '-c client_encoding=utf8'}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class CompanyCRUD:
    def __init__(self):
        self.db: Session = SessionLocal()

    def __del__(self):
        if hasattr(self, 'db'):
            self.db.close()

    def create(self, company_data: dict) -> Company:
        """새로운 회사를 생성합니다."""
        try:
            # 회사명 중복 검사
            if self._get_company_by_name(company_data["company_name"]):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="이미 등록된 회사명입니다."
                )

            company = Company(**company_data)
            self.db.add(company)
            self.db.commit()
            self.db.refresh(company)
            return company
        except Exception as e:
            self.db.rollback()
            raise e

    def get_by_id(self, company_id: UUID) -> Company:
        """ID로 회사를 조회합니다."""
        company = self.db.query(Company).filter(Company.company_id == company_id).first()
        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="회사를 찾을 수 없습니다."
            )
        return company

    def get_all(self, skip: int = 0, limit: int = 100) -> List[Company]:
        """모든 회사를 조회합니다."""
        return self.db.query(Company).offset(skip).limit(limit).all()

    def update(self, company_id: UUID, company_data: dict) -> Company:
        """회사 정보를 수정합니다."""
        try:
            company = self.get_by_id(company_id)

            # 회사명 중복 검사
            if "company_name" in company_data:
                existing_company = self._get_company_by_name(company_data["company_name"])
                if existing_company and existing_company.company_id != company_id:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="이미 등록된 회사명입니다."
                    )

            for key, value in company_data.items():
                setattr(company, key, value)

            self.db.commit()
            self.db.refresh(company)
            return company
        except Exception as e:
            self.db.rollback()
            raise e

    def delete(self, company_id: UUID) -> None:
        """회사를 삭제합니다."""
        try:
            company = self.get_by_id(company_id)
            self.db.delete(company)
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            raise e

    def _get_company_by_name(self, name: str) -> Optional[Company]:
        """회사명으로 회사를 조회합니다."""
        return self.db.query(Company).filter(Company.company_name == name).first() 