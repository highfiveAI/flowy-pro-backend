from fastapi import FastAPI, UploadFile, File, Form
from pydantic import BaseModel
from app.api.lang_search import run_langchain_search
from app.models.stt import stt_from_file
from app.models.tagging import tag_chunks_async
from app.services.openai_service import get_gpt_response
from app.services.langchain_service import run_langchain
from app.services.mcp_service import create_user_context
import os

app = FastAPI()

class PromptRequest(BaseModel):
    prompt: str

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

# === AI API 테스트용 엔드포인트 ===
@app.post("/test/openai")
def test_openai(request: PromptRequest):
    result = get_gpt_response(request.prompt)
    return {"result": result}

@app.post("/test/langchain")
def test_langchain(request: PromptRequest):
    result = run_langchain(request.prompt)
    return {"result": result}

@app.post("/test/mcp")
def test_mcp(request: PromptRequest):
    # MCP는 예시로 context 생성 결과 반환
    result = create_user_context("test_user", {"prompt": request.prompt})
    return {"result": str(result)}

    