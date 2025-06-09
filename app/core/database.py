# 임시 파일입니다 추후 삭제할게요 - 선아

# from sqlalchemy import create_engine
# from sqlalchemy.orm import sessionmaker
# from app.core.config import settings

# # psycopg2 connect_args 설정 추가
# engine = create_engine(
#     settings.CONNECTION_STRING,
#     connect_args={'options': '-c client_encoding=utf8'}
# )

# SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# def get_db():
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close() 