from typing import List, Optional
from uuid import UUID
from fastapi import HTTPException, status
import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.future import select
from app.core.config import settings
from app.models.company_position import CompanyPosition

# DB 연결 설정 (비동기)
DB_URL = settings.CONNECTION_STRING.replace('postgresql://', 'postgresql+asyncpg://')
engine = create_async_engine(
    DB_URL,
    echo=True
)
AsyncSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


class PositionCRUD:
    def __init__(self):
        self.db: AsyncSession = AsyncSessionLocal()
        # 기본 회사 ID 설정
        self.default_company_id = UUID("7e48a91a-99a9-4013-9015-6281b72920a9")

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.db.close()

    async def create(self, position_data: dict) -> CompanyPosition:
        """새로운 직급을 생성합니다."""
        try:
            # 직급 코드 중복 검사
            existing_position = await self._get_position_by_code(position_data["position_code"])
            if existing_position:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="이미 등록된 직급 코드입니다."
                )

            # position_company_id 기본값 설정
            position_data["position_company_id"] = self.default_company_id

            position = CompanyPosition(**position_data)
            self.db.add(position)
            await self.db.commit()
            await self.db.refresh(position)
            return position
        except Exception as e:
            await self.db.rollback()
            raise e

    async def get_by_id(self, position_id: UUID) -> CompanyPosition:
        """ID로 직급을 조회합니다."""
        query = select(CompanyPosition).filter(CompanyPosition.position_id == position_id)
        result = await self.db.execute(query)
        position = result.scalar_one_or_none()
        
        if not position:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="직급을 찾을 수 없습니다."
            )
        return position

    async def get_all(self, skip: int = 0, limit: int = 100) -> List[CompanyPosition]:
        """모든 직급을 조회합니다."""
        query = select(CompanyPosition).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def update(self, position_id: UUID, position_data: dict) -> CompanyPosition:
        """직급 정보를 수정합니다."""
        try:
            position = await self.get_by_id(position_id)

            # 직급 코드 중복 검사
            if "position_code" in position_data:
                existing_position = await self._get_position_by_code(position_data["position_code"])
                if existing_position and existing_position.position_id != position_id:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="이미 등록된 직급 코드입니다."
                    )

            for key, value in position_data.items():
                setattr(position, key, value)

            await self.db.commit()
            await self.db.refresh(position)
            return position
        except Exception as e:
            await self.db.rollback()
            raise e

    async def delete(self, position_id: UUID) -> None:
        """직급을 삭제합니다."""
        try:
            position = await self.get_by_id(position_id)
            await self.db.delete(position)
            await self.db.commit()
        except Exception as e:
            await self.db.rollback()
            raise e

    async def _get_position_by_code(self, code: str) -> Optional[CompanyPosition]:
        """직급 코드로 직급을 조회합니다."""
        query = select(CompanyPosition).filter(CompanyPosition.position_code == code)
        result = await self.db.execute(query)
        return result.scalar_one_or_none() 