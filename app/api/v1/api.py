from fastapi import APIRouter
from app.api.v1.endpoints import search
from app.api.v1.endpoints import speech_to_text
from app.api.v1.endpoints import docs
from app.api.v1.endpoints import user
from app.api.v1.endpoints import admin
from app.api.v1.endpoints import project

api_router = APIRouter()
api_router.include_router(search.router, prefix="/search", tags=["lang_search_test"])
api_router.include_router(speech_to_text.router, prefix="/stt", tags=["speech_to_text"])
api_router.include_router(docs.router, prefix="/docs", tags=["docs"])
api_router.include_router(user.router, prefix="/users", tags=["Users"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_router.include_router(project.router, prefix="/projects", tags=["projects"])