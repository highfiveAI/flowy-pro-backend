from fastapi import FastAPI
import os
from dotenv import load_dotenv
load_dotenv()
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.api import api_router
# import uvicorn

app = FastAPI(
    title="FlowyPro API",
    description="FlowyPro 내부 문서 추천 시스템 API",
    version="1.0.0"
)

app.include_router(api_router, prefix="/api")

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # React 개발 서버
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """API 상태 확인용 엔드포인트"""
    return {"status": "running", "service": "FlowyPro Document Recommendation API"}
    
# if __name__ == "__main__":
    # uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)

    