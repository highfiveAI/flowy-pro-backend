from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# settings.CONNECTION_STRING에 맞게 설정
from app.core.config import settings

engine = create_engine(settings.CONNECTION_STRING)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
