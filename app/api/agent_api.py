from fastapi import APIRouter, Request
from app.models.tagging import tag_chunks_async
from langchain.agents import initialize_agent, Tool, AgentType
from langchain.llms import OpenAI

router = APIRouter()

@router.post("/lang-summary")
async def lang_summary_api(request: Request):
    data = await request.json()
    subject = data.get("subject")
    chunks = data.get("chunks")
    tag_result = data.get("tag_result")
    result = await lang_summary_internal(subject, chunks, tag_result)
    return result

async def lang_summary_internal(subject, chunks, tag_result=None):
    if tag_result is None:
        tag_result = await tag_chunks_async(subject, chunks)
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
    agent_output = agent.run("이 회의의 핵심 요약을 해줘.")
    return {"agent_output": agent_output, "tag_result": tag_result} 