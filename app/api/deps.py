from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy import create_engine
from app.db.session import get_db
from app.core.config import settings
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.db_session import get_db_session

engine = create_engine(settings.CONNECTION_STRING)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

async def get_db() -> AsyncSession:
    async for session in get_db_session():
        try:
            yield session
        finally:
            await session.close()