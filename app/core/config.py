import os
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

class Settings:
    PROJECT_NAME: str = "FastAPI Project"
    VERSION: str = "0.1.0"
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY")
    SERPAPI_API_KEY: str = os.getenv("SERPAPI_API_KEY")
    CONNECTION_STRING: str = os.getenv("CONNECTION_STRING")

    SECRET_KEY: str = os.getenv("SECRET_KEY")
    GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET: str = os.getenv("GOOGLE_CLIENT_SECRET")
    GOOGLE_REDIRECT_URI: str = os.getenv("GOOGLE_REDIRECT_URI")
    FRONTEND_URI: str = os.getenv("FRONTEND_URI")
    BACKEND_URI: str = os.getenv("BACKEND_URI")
    POSTGRES_USER: str = os.getenv("POSTGRES_USER")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB")
    POSTGRES_PORT: str = os.getenv("POSTGRES_PORT")
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST")
    COOKIE_SECURE: str = os.getenv("COOKIE_SECURE")
    COOKIE_SAMESITE: str = os.getenv("COOKIE_SAMESITE")

    # 여기에 추가 환경변수 및 공통 설정 작성 가능

settings = Settings() 