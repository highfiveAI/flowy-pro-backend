from fastapi import APIRouter, HTTPException, Depends
from app.services.search_service.lang_array_search import run_batch_keyword_search
from app.services.search_service.lang_search import run_single_keyword_search
from app.services.search_service.lang_graph_search import search_graph
from typing import List, Dict, Optional
from pydantic import BaseModel
from app.db.db_session import get_db_session
from app.services.tagging import save_prompt_log
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

router = APIRouter()

class KeywordRequest(BaseModel):
    keywords: List[str]

class SearchRequest(BaseModel):
    query: str
    meeting_id: Optional[str] = None

class SearchResponse(BaseModel):
    result: str

@router.post("/")
async def get_websearch(
    query: str, 
    meeting_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db_session)
):
    """Runs the Langchain agent from lang_search.py with the given query."""
    
    # ========== Search Agent 시작/완료 시간 추적 ==========
    search_start_time = datetime.now()
    print(f"[Search API] Search Agent 시작: {search_start_time}", flush=True)
    
    result = await run_single_keyword_search(query)
    
    search_end_time = datetime.now()
    print(f"[Search API] Search Agent 완료: {search_end_time} (소요시간: {search_end_time - search_start_time})", flush=True)
    
    # ========== Search Agent 프롬프트 로그 저장 ==========
    if meeting_id:
        await save_prompt_log(
            db, 
            meeting_id, 
            "search", 
            {
                "query": query,
                "result": result
            },
            input_date=search_start_time,
            output_date=search_end_time
        )
    
    return {"query": query, "response": result}

@router.post("/search")
async def search_resume_links(payload: SearchRequest, db: AsyncSession = Depends(get_db_session)):
    
    # ========== Search Agent 시작/완료 시간 추적 ==========
    search_start_time = datetime.now()
    print(f"[Search API] Graph Search Agent 시작: {search_start_time}", flush=True)
    
    result = await search_graph.ainvoke({"query": payload.query})
    
    search_end_time = datetime.now()
    print(f"[Search API] Graph Search Agent 완료: {search_end_time} (소요시간: {search_end_time - search_start_time})", flush=True)
    
    # ========== Search Agent 프롬프트 로그 저장 ==========
    if payload.meeting_id:
        await save_prompt_log(
            db, 
            payload.meeting_id, 
            "search", 
            {
                "query": payload.query,
                "valid_links": result.get("valid_links", [])
            },
            input_date=search_start_time,
            output_date=search_end_time
        )
    
    return {
        "valid_links": result.get("valid_links", [])
    }

@router.post("/api/v1/search/search-links", response_model=SearchResponse)
async def search_links(keywords: List[str]):
    result = await run_batch_keyword_search(keywords)
    return {"result": result}
