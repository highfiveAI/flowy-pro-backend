from fastapi import APIRouter, Request
from app.models.tagging import tag_chunks_async
from langchain.agents import initialize_agent, Tool, AgentType
from langchain.llms import OpenAI
import asyncio

router = APIRouter()

@router.post("/lang-summary")
async def lang_summary(request: Request):
    data = await request.json()
    subject = data.get("subject")
    chunks = data.get("chunks")
    # tagging.py의 결과물 가져오기
    tag_result = await tag_chunks_async(subject, chunks)

    # LangChain Agent 예시 (OpenAI LLM 사용)
    llm = OpenAI(temperature=0)
    tools = [
        Tool(
            name="TagResult",
            func=lambda x: str(tag_result),
            description="tag_chunks_async의 결과를 반환"
        )
    ]
    agent = initialize_agent(
        tools, llm, agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION, verbose=True
    )

    # agent 실행 예시
    agent_output = agent.run("이 회의의 핵심 요약을 해줘.")

    return {"agent_output": agent_output, "tag_result": tag_result} 