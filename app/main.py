from fastapi import FastAPI, UploadFile, File, Form
from app.api.lang_search import run_langchain_search
from app.models.stt import stt_from_file
from app.models.tagging import tag_chunks_async
from app.api.mcp_api import router as mcp_router
from app.api.openai_api import router as openai_router
from app.api.langchain_api import router as langchain_router
import os

app = FastAPI()
app.include_router(mcp_router)
app.include_router(openai_router)
app.include_router(langchain_router)

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.get("/search/")
def search_endpoint(query: str):
    """Runs the Langchain agent from lang_search.py with the given query."""
    return {"query": query, "response": run_langchain_search(query)}

@app.post("/stt")
async def stt_api(file: UploadFile = File(...), subject: str = Form(None)):
    print("=== stt_api called ===", flush=True)
    temp_path = f"temp_{file.filename}"
    with open(temp_path, "wb") as f:
        f.write(await file.read())
    result = stt_from_file(temp_path)
    os.remove(temp_path)
    print("subject:", subject, "chunks in result:", "chunks" in result, flush=True)
    tag_result = None
    if subject and "chunks" in result:
        print("calling tag_chunks...", flush=True)
        tag_result = await tag_chunks_async(subject, result["chunks"])
    else:
        print("tag_chunks 조건 불충분", flush=True)
    return {**result, "tagging": tag_result}

    