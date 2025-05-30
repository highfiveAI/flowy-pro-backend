from fastapi import APIRouter
from pydantic import BaseModel
from app.services.langchain_service import run_langchain

router = APIRouter()

class PromptRequest(BaseModel):
    prompt: str

@router.post("/test/langchain")
def test_langchain(request: PromptRequest):
    result = run_langchain(request.prompt)
    return {"result": result} 