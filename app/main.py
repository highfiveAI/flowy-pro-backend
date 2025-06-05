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
from app.api.v1.api import api_router


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 또는 ["http://localhost:5173"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")




@app.get("/")
def read_root():
    return {"Hello": "World"}

    