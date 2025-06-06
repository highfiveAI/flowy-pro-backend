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
    # 여기에 추가 환경변수 및 공통 설정 작성 가능

settings = Settings() 