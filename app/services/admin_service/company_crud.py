from typing import List, Optional
from uuid import UUID
from datetime import datetime
from fastapi import HTTPException, status
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.future import select

from app.core.config import settings
from app.models.company import Company

load_dotenv()

DB_URL = settings.CONNECTION_STRING.replace('postgresql://', 'postgresql+asyncpg://')
engine = create_async_engine(
    DB_URL,
    echo=True
)
AsyncSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


class CompanyCRUD:
    def __init__(self):
        self.db: AsyncSession = AsyncSessionLocal()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.db.close()

    async def create(self, company_data: dict) -> Company:
        """새로운 회사를 생성합니다."""
        try:
            # 회사명 중복 검사
            existing_company = await self._get_company_by_name(company_data["company_name"])
            if existing_company:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="이미 등록된 회사명입니다."
                )

            company = Company(**company_data)
            self.db.add(company)
            await self.db.commit()
            await self.db.refresh(company)
            return company
        except Exception as e:
            await self.db.rollback()
            raise e

    async def get_by_id(self, company_id: UUID) -> Company:
        """ID로 회사를 조회합니다."""
        query = select(Company).filter(Company.company_id == company_id)
        result = await self.db.execute(query)
        company = result.scalar_one_or_none()
        
        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="회사를 찾을 수 없습니다."
            )
        return company

    async def get_all(self, skip: int = 0, limit: int = 100) -> List[Company]:
        """모든 회사를 조회합니다."""
        query = select(Company).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def update(self, company_id: UUID, company_data: dict) -> Company:
        """회사 정보를 수정합니다."""
        try:
            company = await self.get_by_id(company_id)

            # 회사명 중복 검사
            if "company_name" in company_data:
                existing_company = await self._get_company_by_name(company_data["company_name"])
                if existing_company and existing_company.company_id != company_id:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="이미 등록된 회사명입니다."
                    )

            for key, value in company_data.items():
                setattr(company, key, value)

            await self.db.commit()
            await self.db.refresh(company)
            return company
        except Exception as e:
            await self.db.rollback()
            raise e

    async def delete(self, company_id: UUID) -> None:
        """회사를 삭제합니다."""
        try:
            company = await self.get_by_id(company_id)
            await self.db.delete(company)
            await self.db.commit()
        except Exception as e:
            await self.db.rollback()
            raise e

    async def _get_company_by_name(self, name: str) -> Optional[Company]:
        """회사명으로 회사를 조회합니다."""
        query = select(Company).filter(Company.company_name == name)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def update_service_status(self, company_id: UUID, service_status: bool, service_enddate: datetime | None = None) -> Company:
        """회사의 서비스 상태를 변경합니다."""
        try:
            company = await self.get_by_id(company_id)
            company.service_status = service_status
            
            if not service_status and service_enddate:
                company.service_enddate = service_enddate
            
            await self.db.commit()
            await self.db.refresh(company)
            return company
        except Exception as e:
            await self.db.rollback()
            raise e 