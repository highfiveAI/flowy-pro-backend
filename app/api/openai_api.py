from fastapi import APIRouter
from pydantic import BaseModel
from app.services.openai_service import get_gpt_response

router = APIRouter()

class PromptRequest(BaseModel):
    prompt: str

@router.post("/test/openai")
def test_openai(request: PromptRequest):
    result = get_gpt_response(request.prompt)
    return {"result": result} 