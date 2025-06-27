from fastapi import APIRouter, HTTPException
from app.services.search_service.lang_array_search import run_batch_keyword_search
from app.services.search_service.lang_search import run_langchain_search
from app.services.search_service.lang_graph_search import search_graph
from typing import List, Dict
from pydantic import BaseModel

router = APIRouter()

class KeywordRequest(BaseModel):
    keywords: List[str]

class SearchRequest(BaseModel):
    query: str

@router.post("/")
async def get_websearch(query: str):
    """Runs the Langchain agent from lang_search.py with the given query."""
    result = await run_langchain_search(query)
    return {"query": query, "response": result}

@router.post("/search")
async def search_resume_links(payload: SearchRequest):
    result = await search_graph.ainvoke({"query": payload.query})
    return {
        "valid_links": result.get("valid_links", [])
    }

@router.post("/search-links", response_model=Dict[str, List[str]])
async def search_links(request: KeywordRequest):
    try:
        results = await run_batch_keyword_search(
            keywords=request.keywords,
        )
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"검색 중 오류 발생: {str(e)}")