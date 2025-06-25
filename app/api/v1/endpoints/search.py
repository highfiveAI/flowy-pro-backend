from fastapi import APIRouter
from app.services.search_service.lang_search import run_langchain_search
from app.services.search_service.lang_graph_search import search_graph
from pydantic import BaseModel

router = APIRouter()


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