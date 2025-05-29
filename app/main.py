from fastapi import FastAPI
from app.api.lang_search import run_langchain_search

app = FastAPI()

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.get("/search/")
def search_endpoint(query: str):
    """Runs the Langchain agent from lang_search.py with the given query."""
    return {"query": query, "response": run_langchain_search(query)}

