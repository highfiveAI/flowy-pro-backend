from fastapi import APIRouter
from pydantic import BaseModel
from app.services.mcp_service import create_user_context

router = APIRouter()

class PromptRequest(BaseModel):
    prompt: str

@router.post("/test/mcp")
def test_mcp(request: PromptRequest):
    # MCP는 예시로 context 생성 결과 반환
    result = create_user_context("test_user", {"prompt": request.prompt})
    return {"result": str(result)} 