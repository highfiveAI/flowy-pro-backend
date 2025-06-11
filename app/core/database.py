# 임시 파일입니다 추후 삭제할게요 - 선아

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# 비동기 데이터베이스 엔진 생성
engine = create_async_engine(
    settings.ASYNC_CONNECTION_STRING,
    echo=True,
    future=True
)

# 비동기 세션 생성
async_session = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# 비동기 데이터베이스 세션 의존성
async def get_db() -> AsyncSession:
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close() 