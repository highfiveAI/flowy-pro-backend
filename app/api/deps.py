from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy import create_engine
from app.db.session import get_db
from app.core.config import settings

engine = create_engine(settings.CONNECTION_STRING)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db_session() -> Session:
    db = next(get_db())
    try:
        yield db
    finally:
        db.close()
