from fastapi import FastAPI, Request, APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.db_session import get_db_session
from app.services.chatbot_service.scenario import agent

from app.services.chatbot_service.scenario_crud import search_similar_scenario
from langchain.embeddings import HuggingFaceEmbeddings

router = APIRouter()

# 임베딩 모델 준비 (1회 초기화)
embedding_model = HuggingFaceEmbeddings(model_name="sentence-transformers/distiluse-base-multilingual-cased-v2")

class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    message: str

@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest):
    user_input = req.message
    response = await agent.arun(user_input)
    return ChatResponse(message=response)

@router.post("/chat/embed")
async def chat_with_vector_search(req: ChatRequest, db: AsyncSession = Depends(get_db_session)):
    user_input = req.message

    # 1. 사용자 질문에 대한 임베딩 생성
    query_embedding = embedding_model.embed_query(user_input)

    # 2. 유사한 시나리오 검색
    scenario = await search_similar_scenario(db, query_embedding)

    if scenario:
        return {
            "match": True,
            "scenario_name": scenario.scenario_name,
            "content": scenario.content
        }
    else:
        return {
            "match": False,
            "message": "유사한 시나리오를 찾을 수 없습니다."
        }
