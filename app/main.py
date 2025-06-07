from fastapi import FastAPI
# , UploadFile, File, Form, HTTPException, Request, Depends
import os
from dotenv import load_dotenv
load_dotenv()
# from app.api.stt import stt_from_file
# from app.api.tagging import tag_chunks_async
# import json
# from typing import List
# from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from app.api.v1.api import api_router


app = FastAPI()

# 허용할 프론트엔드 주소 (Vite는 보통 5173 포트)
origins = [
    "http://localhost:5173",  # Vite dev server
]

# CORS 미들웨어 추가
app.add_middleware(SessionMiddleware, secret_key="your-session-secret")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(api_router, prefix="/api/v1")




@app.get("/")
def read_root():
    return {"Hello": "World"}

    