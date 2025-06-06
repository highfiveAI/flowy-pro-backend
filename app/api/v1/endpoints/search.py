from fastapi import APIRouter
from app.services.lang_search import run_langchain_search

router = APIRouter()

@router.post("/")
def get_websearch(query: str):
    """Runs the Langchain agent from lang_search.py with the given query."""
    return {"query": query, "response": run_langchain_search(query)}
